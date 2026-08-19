"""Generatywny symulator stabilnych reżimów pracy falownika Deye.

Moduł uczy zachowania falownika na podstawie historycznych plików CSV, zapisuje
wytrenowany model i generuje nowe sekwencje bez ponownego dostarczania danych.
Sensory PV i baterii pomagają rozdzielać reżimy podczas uczenia, ale nigdy nie są
zwracane w wygenerowanych próbkach.

Generator nie oblicza mocy pozornej ani biernej. Jego wyjście jest stabilnym
bodźcem wejściowym do późniejszego testowania niezależnych modeli obliczeniowych.
"""

from __future__ import annotations

import argparse
import json
import pickle
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd

MODEL_FORMAT_VERSION=3

PHASES=("l1", "l2", "l3")
INTERVENTION_FILE_PATTERN=re.compile(r"^czajnik.*\.csv$", re.IGNORECASE)


class OperatingMode(str, Enum):
	"""Publiczne tryby symulacji."""

	GRID_ON="grid_on"
	GRID_ON_IMPORT="grid_on_import"
	GRID_ON_EXPORT="grid_on_export"
	GRID_ON_IDLE="grid_on_idle"
	GRID_OFF="grid_off"


TRAINING_ONLY_SENSORS=frozenset(
	{
		"sensor.deye_pv_power",
		"sensor.deye_battery_power",
	}
)

EXCLUDED_OUTPUT_SENSORS=frozenset(
	{
		"sensor.deye_pv_power",
		"sensor.deye_battery_power",
		"sensor.deye_q_prime_l1_reactive_power",
		"sensor.deye_q_prime_l2_reactive_power",
		"sensor.deye_q_prime_l3_reactive_power",
		"sensor.deye_q_prime_l1_apparent_power",
		"sensor.deye_q_prime_l2_apparent_power",
		"sensor.deye_q_prime_l3_apparent_power",
		"sensor.deye_q_prime_l1_validity_margin",
		"sensor.deye_q_prime_l2_validity_margin",
		"sensor.deye_q_prime_l3_validity_margin",
		"sensor.deye_q_prime_total_reactive_power",
		"sensor.deye_diag_l1_inner_power_balance_error",
		"sensor.deye_diag_l2_inner_power_balance_error",
		"sensor.deye_diag_l3_inner_power_balance_error",
	}
)

GRID_VOLTAGE_SENSORS=(
	"sensor.deye_grid_l1_voltage",
	"sensor.deye_grid_l2_voltage",
	"sensor.deye_grid_l3_voltage",
)

GRID_PHASE_POWER_SENSORS=(
	"sensor.deye_grid_l1_power",
	"sensor.deye_grid_l2_power",
	"sensor.deye_grid_l3_power",
)

CLASSIFICATION_SENSORS=frozenset(
	set(TRAINING_ONLY_SENSORS)|set(GRID_VOLTAGE_SENSORS)|set(GRID_PHASE_POWER_SENSORS)
)

DETAILED_GRID_ON_MODES=(
	OperatingMode.GRID_ON_IMPORT,
	OperatingMode.GRID_ON_EXPORT,
	OperatingMode.GRID_ON_IDLE,
)

MODE_ALIASES={
	"grid_on":OperatingMode.GRID_ON,
	"gridon":OperatingMode.GRID_ON,
	"on":OperatingMode.GRID_ON,
	"grid_on_import":OperatingMode.GRID_ON_IMPORT,
	"grid_import":OperatingMode.GRID_ON_IMPORT,
	"import":OperatingMode.GRID_ON_IMPORT,
	"grid_on_export":OperatingMode.GRID_ON_EXPORT,
	"grid_export":OperatingMode.GRID_ON_EXPORT,
	"export":OperatingMode.GRID_ON_EXPORT,
	"grid_on_idle":OperatingMode.GRID_ON_IDLE,
	"grid_idle":OperatingMode.GRID_ON_IDLE,
	"idle":OperatingMode.GRID_ON_IDLE,
	"grid_off":OperatingMode.GRID_OFF,
	"gridoff":OperatingMode.GRID_OFF,
	"off":OperatingMode.GRID_OFF,
}


class DeyeModelError(RuntimeError):
	"""Błąd modelu, danych lub generowania."""


class DataQualityError(DeyeModelError):
	"""Dane nie wystarczają do wiarygodnego uczenia albo generowania."""


class UnsupportedModeError(DeyeModelError):
	"""Żądany tryb nie jest obsługiwany lub nie został zaobserwowany."""


class InterventionUnavailableError(DeyeModelError):
	"""Brak rzeczywistych par przed/po do modelowania interwencji czynnej."""


@dataclass(frozen=True)
class ModelConfig:
	"""Parametry synchronizacji, identyfikacji reżimów i generatora VAR."""

	frequency:str="5s"
	max_staleness:str="65s"
	minimum_training_samples:int=100
	minimum_generated_samples:int=100
	minimum_stable_run_samples:int=6
	stability_confirmation_samples:int=3
	stability_change_quantile:float=0.98
	stability_mad_multiplier:float=12.0
	stability_minimum_score:float=3.0
	grid_voltage_on_v:float=180.0
	grid_voltage_off_v:float=50.0
	grid_flow_deadband_w:float=150.0
	pv_activity_threshold_w:float=150.0
	battery_activity_threshold_w:float=150.0
	ridge:float=0.01
	maximum_spectral_radius:float=0.98
	clip_quantile:float=0.005
	power_residual_clip_quantile:float=0.01

	def validate(self)->None:
		frequency=pd.to_timedelta(self.frequency)
		if frequency <= pd.Timedelta(0):
			raise ValueError("frequency musi być dodatnie")
		if pd.to_timedelta(self.max_staleness) < frequency:
			raise ValueError("max_staleness nie może być krótsze niż frequency")
		if self.minimum_training_samples < 20:
			raise ValueError("minimum_training_samples nie może być mniejsze niż 20")
		if self.minimum_generated_samples < 100:
			raise ValueError("minimum_generated_samples nie może być mniejsze niż 100")
		if self.minimum_stable_run_samples < 2:
			raise ValueError("minimum_stable_run_samples musi wynosić co najmniej 2")
		if self.stability_confirmation_samples < 2:
			raise ValueError("stability_confirmation_samples musi wynosić co najmniej 2")
		if not 0.5 < self.stability_change_quantile < 1.0:
			raise ValueError("stability_change_quantile musi należeć do (0.5, 1.0)")
		if self.stability_mad_multiplier <= 0.0:
			raise ValueError("stability_mad_multiplier musi być dodatnie")
		if self.stability_minimum_score <= 0.0:
			raise ValueError("stability_minimum_score musi być dodatnie")
		if self.grid_voltage_off_v >= self.grid_voltage_on_v:
			raise ValueError("Próg grid_off musi być niższy niż próg grid_on")
		if self.ridge <= 0.0:
			raise ValueError("ridge musi być dodatnie")
		if not 0.0 < self.maximum_spectral_radius < 1.0:
			raise ValueError("maximum_spectral_radius musi należeć do (0, 1)")
		if not 0.0 <= self.clip_quantile < 0.5:
			raise ValueError("clip_quantile musi należeć do [0, 0.5)")
		if not 0.0 <= self.power_residual_clip_quantile < 0.5:
			raise ValueError("power_residual_clip_quantile musi należeć do [0, 0.5)")


@dataclass
class _RegimeModel:
	"""Parametry jednego stabilnego reżimu VAR(1)."""

	mode:str
	training_samples:int
	training_segments:int
	center:np.ndarray
	scale:np.ndarray
	intercept:np.ndarray
	transition:np.ndarray
	residuals:np.ndarray
	start_states:np.ndarray
	lower:np.ndarray
	upper:np.ndarray
	observed_mean:np.ndarray
	observed_std:np.ndarray
	power_residual_names:tuple[str, ...]
	power_residuals:np.ndarray


class DeyeModel:
	"""Wielowymiarowy generator stabilnego zachowania falownika."""

	def __init__(self, config:ModelConfig | None=None)->None:
		self.config=config or ModelConfig()
		self.config.validate()
		self.feature_columns:list[str]=[]
		self.regime_models:dict[str, _RegimeModel]={}
		self.mode_weights:dict[str, float]={}
		self.quality_report:dict[str, object]={}
		self.source_files:list[str]=[]
		self.intervention_source_files:list[str]=[]
		self.intervention_models:dict[str, object]={}
		self.is_fitted=False

	@classmethod
	def from_csv_files(
		cls,
		paths:str | Path | Iterable[str | Path],
		config:ModelConfig | None=None,
	)->DeyeModel:
		model=cls(config=config)
		model.fit(paths)
		return model

	def fit(self, paths:str | Path | Iterable[str | Path])->DeyeModel:
		files=self._resolve_csv_files(paths)
		long_data=self._read_long_csv(files)
		wide=self._synchronize(long_data)
		mode, hidden_state=self._classify(wide)
		stable_mode, segment_id, change_score, change_threshold=self._stable_segments(
			wide,
			mode,
			hidden_state,
		)
		self.regime_models={}
		for candidate in (*DETAILED_GRID_ON_MODES, OperatingMode.GRID_OFF):
			mask=stable_mode == candidate.value
			if int(mask.sum())<self.config.minimum_training_samples:
				continue
			self.regime_models[candidate.value]=self._fit_regime_model(
				wide.loc[mask, self.feature_columns],
				segment_id.loc[mask],
				candidate,
			)
		self._set_mode_weights()
		self._build_quality_report(
			long_data,
			wide,
			mode,
			stable_mode,
			change_score,
			change_threshold,
		)
		self._validate_fitted_model()
		self.is_fitted=True
		return self

	def save(self, path:str | Path)->Path:
		"""Zapisz wytrenowany model. Wczytuj wyłącznie zaufane pliki pickle."""
		self._require_fitted()
		output=Path(path)
		output.parent.mkdir(parents=True, exist_ok=True)
		payload={"format_version":MODEL_FORMAT_VERSION, "model":self}
		with output.open("wb") as stream:
			pickle.dump(payload, stream, protocol=pickle.HIGHEST_PROTOCOL)
		return output

	@classmethod
	def load(cls, path:str | Path)->DeyeModel:
		"""Wczytaj wcześniej zapisany, zaufany model."""
		with Path(path).open("rb") as stream:
			payload=pickle.load(stream)
		if not isinstance(payload, dict) or payload.get("format_version") != MODEL_FORMAT_VERSION:
			raise DeyeModelError("Nieobsługiwany format pliku modelu")
		model=payload.get("model")
		if not isinstance(model, cls):
			raise DeyeModelError("Plik nie zawiera modelu DeyeModel")
		model._require_fitted()
		return model

	def available_modes(self)->dict[str, int]:
		counts={name:model.training_samples for name, model in self.regime_models.items()}
		grid_on_count=sum(counts.get(mode.value, 0) for mode in DETAILED_GRID_ON_MODES)
		if grid_on_count:
			counts={OperatingMode.GRID_ON.value:grid_on_count, **counts}
		return counts

	def generate(
		self,
		modes:str | OperatingMode | Sequence[str | OperatingMode],
		samples_per_mode:int=100,
		random_state:int | None=None,
	)->pd.DataFrame:
		"""Wygeneruj stabilne sekwencje bez danych przejściowych."""
		self._require_fitted()
		if samples_per_mode<self.config.minimum_generated_samples:
			raise ValueError(
				"samples_per_mode musi wynosić co najmniej "
				f"{self.config.minimum_generated_samples}"
			)
		requested=self._normalize_modes(modes)
		rng=np.random.default_rng(random_state)
		parts=[]
		sequence_id=0
		for requested_mode in requested:
			generated, sequence_id=self._generate_requested_mode(
				requested_mode,
				samples_per_mode,
				rng,
				sequence_id,
			)
			parts.append(generated)
		result=pd.concat(parts, ignore_index=True)
		result.insert(0, "sample_index", np.arange(len(result)))
		metadata=[
			"sample_index",
			"mode_sample_index",
			"sequence_id",
			"simulation_time_s",
			"operating_mode",
			"source_regime",
			"model_type",
		]
		return result[metadata+self.feature_columns]

	def apply_active_load(
		self,
		state:pd.Series | Mapping[str, float],
		delta_p:float,
		target_phase:str,
		mode:str | OperatingMode,
		random_state:int | None=None,
	)->pd.Series:
		"""Zastosuj wyuczoną interwencję czynną bez przypisywania Q ani S.

		Interfejs jest celowo niedostępny, dopóki model nie zostanie nauczony na
		rzeczywistych parach czajnikowych. Niedozwolony jest zastępczy skrót
		polegający na ręcznym dodaniu mocy do wybranych rejestrów.
		"""
		self._require_fitted()
		if not isinstance(state, (pd.Series, Mapping)):
			raise TypeError("state musi być obiektem Series albo mapowaniem sensorów")
		if not np.isfinite(delta_p) or delta_p == 0.0:
			raise ValueError("delta_p musi być skończoną wartością różną od zera")
		phase=target_phase.strip().lower()
		if phase not in PHASES:
			raise ValueError("target_phase musi mieć wartość L1, L2 albo L3")
		requested=self._normalize_modes(mode)
		if len(requested) != 1:
			raise ValueError("Interwencja wymaga dokładnie jednego trybu")
		_ = random_state
		key=f"{requested[0].value}|{phase}"
		if key not in self.intervention_models:
			raise InterventionUnavailableError(
				"Brak wyuczonej interwencji dla trybu "
				f"{requested[0].value} i fazy {phase.upper()}. "
				"Dodaj rzeczywiste pliki czajnik*.csv; model nie będzie zastępował ich "
				"sztucznym dodawaniem P."
			)
		raise InterventionUnavailableError("Nieobsługiwany format modelu interwencji")

	def save_generated(
		self,
		output_path:str | Path,
		modes:str | OperatingMode | Sequence[str | OperatingMode],
		samples_per_mode:int=100,
		random_state:int | None=None,
	)->pd.DataFrame:
		generated=self.generate(
			modes=modes,
			samples_per_mode=samples_per_mode,
			random_state=random_state,
		)
		output=Path(output_path)
		output.parent.mkdir(parents=True, exist_ok=True)
		generated.to_csv(output, index=False)
		return generated

	def summary(self)->dict[str, object]:
		self._require_fitted()
		limitations=[
			"Model generuje tylko reżimy zaobserwowane w danych treningowych.",
			"Generator nie wyznacza VA ani var.",
		]
		if OperatingMode.GRID_OFF.value not in self.regime_models:
			limitations.append("Aktualny zbiór nie zawiera fizycznego grid_off.")
		if not self.intervention_models:
			limitations.append(
				"Interwencje czynne wymagają rzeczywistych par z plików czajnik*.csv."
			)
		return {
			"model_format_version":MODEL_FORMAT_VERSION,
			"model_type":"multivariate_var1_residual_bootstrap",
			"source_files":self.source_files,
			"feature_count":len(self.feature_columns),
			"feature_columns":self.feature_columns,
			"training_only_sensors":sorted(TRAINING_ONLY_SENSORS),
			"excluded_output_sensors":sorted(EXCLUDED_OUTPUT_SENSORS),
			"available_modes":self.available_modes(),
			"active_load_intervention":{
				"available":bool(self.intervention_models),
				"source_files":self.intervention_source_files,
				"trained_mode_phase_pairs":sorted(self.intervention_models),
				"ground_truth_q_or_s_used":False,
			},
			"quality":self.quality_report,
			"config":asdict(self.config),
			"limitations":limitations,
		}

	def _resolve_csv_files(
		self,
		paths:str | Path | Iterable[str | Path],
	)->list[Path]:
		items=[paths] if isinstance(paths, (str, Path)) else list(paths)
		files=[]
		for item in items:
			path=Path(item).expanduser()
			if path.is_dir():
				files.extend(sorted(path.glob("*.csv")))
			elif path.is_file():
				files.append(path)
			else:
				files.extend(sorted(path.parent.glob(path.name)))
		unique=sorted({path.resolve() for path in files})
		intervention_files=[path for path in unique if INTERVENTION_FILE_PATTERN.match(path.name)]
		base_files=[path for path in unique if path not in intervention_files]
		self.intervention_source_files=[str(path) for path in intervention_files]
		if not base_files:
			raise FileNotFoundError("Nie znaleziono żadnego pliku CSV")
		self.source_files=[str(path) for path in base_files]
		return base_files

	def _read_long_csv(self, files:Sequence[Path])->pd.DataFrame:
		frames=[]
		for source_order, path in enumerate(files):
			frame=pd.read_csv(
				path,
				usecols=["entity_id", "state", "last_changed"],
				dtype={"entity_id":"string", "state":"string"},
			)
			frame["_source_order"]=source_order
			frames.append(frame)
		data=pd.concat(frames, ignore_index=True)
		data["last_changed"]=pd.to_datetime(data["last_changed"], utc=True, errors="coerce")
		data["value"]=pd.to_numeric(data["state"], errors="coerce")
		data["entity_id"]=data["entity_id"].str.strip()
		data=data.sort_values(["last_changed", "_source_order"])
		return data.drop_duplicates(["last_changed", "entity_id"], keep="last")

	def _synchronize(self, data:pd.DataFrame)->pd.DataFrame:
		available=set(data["entity_id"].dropna().unique())
		missing=sorted(CLASSIFICATION_SENSORS-available)
		if missing:
			raise DataQualityError(
				"Brak sensorów potrzebnych do identyfikacji reżimu: "+", ".join(missing)
			)
		self.feature_columns=sorted(available-EXCLUDED_OUTPUT_SENSORS)
		if not self.feature_columns:
			raise DataQualityError("Brak sensorów wyjściowych")
		required=sorted(set(self.feature_columns)|set(CLASSIFICATION_SENSORS))
		numeric=data[data["last_changed"].notna() & data["value"].notna()]
		numeric=numeric[numeric["entity_id"].isin(required)]
		wide=numeric.pivot_table(
			index="last_changed",
			columns="entity_id",
			values="value",
			aggfunc="last",
		)
		wide=wide.sort_index().resample(self.config.frequency).last()
		frequency=pd.to_timedelta(self.config.frequency)
		limit=max(1, int(pd.to_timedelta(self.config.max_staleness)/frequency))
		wide=wide.ffill(limit=limit).reindex(columns=required)
		return wide.dropna(subset=required)

	def _classify(self, wide:pd.DataFrame)->tuple[pd.Series, pd.Series]:
		voltages=wide[list(GRID_VOLTAGE_SENSORS)]
		grid_power=wide[list(GRID_PHASE_POWER_SENSORS)].sum(axis=1)
		pv=wide["sensor.deye_pv_power"]
		battery=wide["sensor.deye_battery_power"]
		connected=voltages.min(axis=1)>=self.config.grid_voltage_on_v
		disconnected=voltages.max(axis=1)<=self.config.grid_voltage_off_v
		mode=pd.Series("unknown", index=wide.index, dtype="string")
		mode.loc[connected & (grid_power>self.config.grid_flow_deadband_w)]=(
			OperatingMode.GRID_ON_IMPORT.value
		)
		mode.loc[connected & (grid_power<-self.config.grid_flow_deadband_w)]=(
			OperatingMode.GRID_ON_EXPORT.value
		)
		idle=connected & (grid_power.abs()<=self.config.grid_flow_deadband_w)
		mode.loc[idle]=OperatingMode.GRID_ON_IDLE.value
		mode.loc[disconnected]=OperatingMode.GRID_OFF.value
		pv_state=np.where(
			pv>self.config.pv_activity_threshold_w,
			"pv_active",
			"pv_inactive",
		)
		battery_state=np.select(
			[
				battery>self.config.battery_activity_threshold_w,
				battery<-self.config.battery_activity_threshold_w,
			],
			["battery_positive", "battery_negative"],
			default="battery_idle",
		)
		hidden=pd.Series(
			mode.astype(str)+"|"+pd.Series(pv_state, index=wide.index)+"|"+pd.Series(
				battery_state,
				index=wide.index,
			),
			index=wide.index,
			dtype="string",
		)
		return mode, hidden

	def _stable_segments(
		self,
		wide:pd.DataFrame,
		mode:pd.Series,
		hidden_state:pd.Series,
	)->tuple[pd.Series, pd.Series, pd.Series, float]:
		"""Wykryj stabilność na podstawie zaniku zmian, a nie stałego czasu."""
		features=wide[self.feature_columns]
		delta=features.diff().abs().fillna(0.0)
		level_spread=features.quantile(0.95)-features.quantile(0.05)
		typical_delta=delta.quantile(0.75)
		scale=np.maximum(typical_delta.to_numpy(), level_spread.to_numpy()*0.005)
		scale=np.where(np.isfinite(scale) & (scale>1e-9), scale, 1.0)
		normalized=delta.to_numpy(dtype=float)/scale
		change_values=np.nanquantile(normalized, 0.90, axis=1)
		change_score=pd.Series(change_values, index=wide.index, dtype=float).fillna(0.0)
		finite=change_score[np.isfinite(change_score)]
		quantile_limit=float(finite.quantile(self.config.stability_change_quantile))
		median=float(finite.median())
		mad=float(np.median(np.abs(finite.to_numpy()-median)))
		robust_limit=median+self.config.stability_mad_multiplier*1.4826*mad
		learned=min(quantile_limit, robust_limit)
		threshold=max(self.config.stability_minimum_score, learned)
		low_change=change_score<=threshold
		confirmation=self.config.stability_confirmation_samples
		past=low_change.rolling(confirmation, min_periods=confirmation).sum()>=confirmation
		future=(
			low_change.iloc[::-1]
			.rolling(confirmation, min_periods=confirmation)
			.sum()
			.iloc[::-1]
			>=confirmation
		)
		candidate=low_change & past & future & (mode!="unknown")
		candidate &= hidden_state == hidden_state.shift()
		stable_run=(~candidate).cumsum()
		run_size=candidate.groupby(stable_run).transform("sum")
		stable=candidate & (run_size>=self.config.minimum_stable_run_samples)
		abrupt=change_score>threshold
		segment_break=hidden_state.ne(hidden_state.shift())|abrupt|(~stable)
		segment_id=segment_break.cumsum()
		return mode.where(stable, "unknown"), segment_id, change_score, threshold

	def _fit_regime_model(
		self,
		features:pd.DataFrame,
		segment_id:pd.Series,
		mode:OperatingMode,
	)->_RegimeModel:
		values=features.to_numpy(dtype=float)
		center=np.median(values, axis=0)
		q25=np.quantile(values, 0.25, axis=0)
		q75=np.quantile(values, 0.75, axis=0)
		scale=(q75-q25)/1.349
		standard=np.std(values, axis=0, ddof=1)
		scale=np.where(scale>1e-9, scale, standard)
		scale=np.where(scale>1e-9, scale, 1.0)
		standardized=(values-center)/scale
		power_residual_names, power_residuals=self._power_residual_matrix(features)
		if power_residuals.shape[1]:
			clip=self.config.power_residual_clip_quantile
			residual_low=np.quantile(power_residuals, clip, axis=0)
			residual_high=np.quantile(power_residuals, 1.0-clip, axis=0)
			power_residuals=np.clip(power_residuals, residual_low, residual_high)
		previous=[]
		next_values=[]
		starts=[]
		segment_count=0
		for positions in segment_id.groupby(segment_id).groups.values():
			local_indices=features.index.get_indexer(positions)
			local_indices=local_indices[local_indices>=0]
			if len(local_indices)<2:
				continue
			segment=standardized[local_indices]
			previous.append(segment[:-1])
			next_values.append(segment[1:])
			starts.append(segment)
			segment_count+=1
		if not previous:
			raise DataQualityError(f"Brak przejść czasowych dla trybu {mode.value}")
		x=np.vstack(previous)
		y=np.vstack(next_values)
		design=np.column_stack([np.ones(len(x)), x])
		penalty=np.eye(design.shape[1])*self.config.ridge
		penalty[0, 0]=0.0
		coefficients=np.linalg.solve(design.T@design+penalty, design.T@y)
		intercept=coefficients[0]
		transition=coefficients[1:]
		eigenvalues=np.linalg.eigvals(transition)
		radius=float(np.max(np.abs(eigenvalues))) if len(eigenvalues) else 0.0
		if radius>self.config.maximum_spectral_radius:
			transition*=self.config.maximum_spectral_radius/radius
		prediction=intercept+x@transition
		residuals=y-prediction
		residual_low=np.quantile(residuals, 0.005, axis=0)
		residual_high=np.quantile(residuals, 0.995, axis=0)
		residuals=np.clip(residuals, residual_low, residual_high)
		clip=self.config.clip_quantile
		lower=np.quantile(standardized, clip, axis=0)
		upper=np.quantile(standardized, 1.0-clip, axis=0)
		return _RegimeModel(
			mode=mode.value,
			training_samples=len(features),
			training_segments=segment_count,
			center=center,
			scale=scale,
			intercept=intercept,
			transition=transition,
			residuals=residuals,
			start_states=np.vstack(starts),
			lower=lower,
			upper=upper,
			observed_mean=np.mean(values, axis=0),
			observed_std=np.std(values, axis=0, ddof=1),
			power_residual_names=power_residual_names,
			power_residuals=power_residuals,
		)

	def _set_mode_weights(self)->None:
		grid_models={
			mode.value:self.regime_models[mode.value].training_samples
			for mode in DETAILED_GRID_ON_MODES
			if mode.value in self.regime_models
		}
		total=sum(grid_models.values())
		self.mode_weights={
			name:count/total
			for name, count in grid_models.items()
		} if total else {}

	def _generate_requested_mode(
		self,
		requested:OperatingMode,
		count:int,
		rng:np.random.Generator,
		sequence_id:int,
	)->tuple[pd.DataFrame, int]:
		if requested == OperatingMode.GRID_ON:
			if not self.mode_weights:
				raise UnsupportedModeError("Model nie zawiera żadnego reżimu grid_on")
			names=list(self.mode_weights)
			probabilities=np.array([self.mode_weights[name] for name in names])
			allocation=rng.multinomial(count, probabilities/probabilities.sum())
			parts=[]
			mode_index=0
			for name, local_count in zip(names, allocation, strict=True):
				if local_count == 0:
					continue
				part=self._generate_sequence(name, int(local_count), rng)
				part.insert(0, "source_regime", name)
				part.insert(0, "operating_mode", requested.value)
				part.insert(0, "sequence_id", sequence_id)
				part.insert(0, "mode_sample_index", np.arange(mode_index, mode_index+len(part)))
				parts.append(part)
				mode_index+=len(part)
				sequence_id+=1
			return pd.concat(parts, ignore_index=True), sequence_id
		if requested.value not in self.regime_models:
			available=", ".join(self.available_modes()) or "brak"
			raise UnsupportedModeError(
				f"Tryb {requested.value} nie występuje w danych treningowych. Dostępne: {available}"
			)
		part=self._generate_sequence(requested.value, count, rng)
		part.insert(0, "source_regime", requested.value)
		part.insert(0, "operating_mode", requested.value)
		part.insert(0, "sequence_id", sequence_id)
		part.insert(0, "mode_sample_index", np.arange(len(part)))
		return part, sequence_id+1

	def _generate_sequence(
		self,
		regime_name:str,
		count:int,
		rng:np.random.Generator,
	)->pd.DataFrame:
		model=self.regime_models[regime_name]
		state=model.start_states[int(rng.integers(0, len(model.start_states)))].copy()
		states=np.empty((count, len(self.feature_columns)), dtype=float)
		for index in range(count):
			if index:
				accepted=False
				for _ in range(100):
					residual=model.residuals[int(rng.integers(0, len(model.residuals)))]
					candidate=model.intercept+state@model.transition+residual
					candidate=np.clip(candidate, model.lower, model.upper)
					values=model.center+candidate*model.scale
					if self._state_matches_mode(values, regime_name):
						state=candidate
						accepted=True
						break
				if not accepted:
					state=model.start_states[int(rng.integers(0, len(model.start_states)))].copy()
			states[index]=state
		values=model.center+states*model.scale
		frame=pd.DataFrame(values, columns=self.feature_columns)
		self._apply_empirical_power_residuals(frame, model, rng)
		frame.insert(0, "model_type", "var1_residual_bootstrap")
		step_seconds=pd.to_timedelta(self.config.frequency).total_seconds()
		frame.insert(0, "simulation_time_s", np.arange(count)*step_seconds)
		return frame

	def _power_residual_matrix(self, frame:pd.DataFrame)->tuple[tuple[str, ...], np.ndarray]:
		residuals:dict[str, pd.Series]={}
		for phase in PHASES:
			load=f"sensor.deye_load_{phase}_power"
			grid=f"sensor.deye_grid_{phase}_power"
			inverter=f"sensor.deye_inverter_{phase}_power"
			if {load, grid, inverter}<=set(frame.columns):
				residuals[f"phase_{phase}"]=frame[load]-frame[grid]-frame[inverter]
		for prefix in ("grid", "inverter", "load"):
			total=f"sensor.deye_{prefix}_power"
			phases=[f"sensor.deye_{prefix}_{phase}_power" for phase in PHASES]
			if total in frame.columns and set(phases)<=set(frame.columns):
				residuals[f"total_{prefix}"]=frame[total]-frame[phases].sum(axis=1)
		if not residuals:
			return (), np.empty((len(frame), 0), dtype=float)
		names=tuple(residuals)
		return names, pd.DataFrame(residuals, index=frame.index).to_numpy(dtype=float)

	def _apply_empirical_power_residuals(
		self,
		frame:pd.DataFrame,
		model:_RegimeModel,
		rng:np.random.Generator,
	)->None:
		"""Odtwórz wspólny rozkład błędów rejestrów mocy z danych stabilnych."""
		if model.power_residuals.shape[1] == 0:
			return
		indices=rng.integers(0, len(model.power_residuals), size=len(frame))
		draws=model.power_residuals[indices]
		residual={name:draws[:, index] for index, name in enumerate(model.power_residual_names)}
		for phase in PHASES:
			name=f"phase_{phase}"
			load=f"sensor.deye_load_{phase}_power"
			grid=f"sensor.deye_grid_{phase}_power"
			inverter=f"sensor.deye_inverter_{phase}_power"
			if name in residual and {load, grid, inverter}<=set(frame.columns):
				frame[load]=frame[grid]+frame[inverter]+residual[name]
		for prefix in ("grid", "inverter", "load"):
			name=f"total_{prefix}"
			total=f"sensor.deye_{prefix}_power"
			phases=[f"sensor.deye_{prefix}_{phase}_power" for phase in PHASES]
			if name in residual and total in frame.columns and set(phases)<=set(frame.columns):
				frame[total]=frame[phases].sum(axis=1)+residual[name]

	def _state_matches_mode(self, values:np.ndarray, regime_name:str)->bool:
		lookup={name:values[index] for index, name in enumerate(self.feature_columns)}
		voltages=np.array([lookup[name] for name in GRID_VOLTAGE_SENSORS])
		grid_power=sum(lookup[name] for name in GRID_PHASE_POWER_SENSORS)
		if regime_name == OperatingMode.GRID_OFF.value:
			return bool(voltages.max()<=self.config.grid_voltage_off_v)
		if voltages.min()<self.config.grid_voltage_on_v:
			return False
		if regime_name == OperatingMode.GRID_ON_IMPORT.value:
			return grid_power>self.config.grid_flow_deadband_w
		if regime_name == OperatingMode.GRID_ON_EXPORT.value:
			return grid_power<-self.config.grid_flow_deadband_w
		if regime_name == OperatingMode.GRID_ON_IDLE.value:
			return abs(grid_power)<=self.config.grid_flow_deadband_w
		return False

	def _normalize_modes(
		self,
		modes:str | OperatingMode | Sequence[str | OperatingMode],
	)->list[OperatingMode]:
		if isinstance(modes, OperatingMode):
			items=[modes]
		elif isinstance(modes, str):
			items=[item for item in re.split(r"\s*\+\s*|\s*,\s*", modes) if item]
		else:
			items=list(modes)
		if not items:
			raise UnsupportedModeError("Lista trybów jest pusta")
		result=[]
		for item in items:
			if isinstance(item, OperatingMode):
				result.append(item)
				continue
			key=str(item).strip().lower().replace("-", "_").replace(" ", "_")
			key=re.sub(r"_+", "_", key)
			if key not in MODE_ALIASES:
				raise UnsupportedModeError(f"Nieobsługiwany tryb: {item}")
			result.append(MODE_ALIASES[key])
		return result

	def _build_quality_report(
		self,
		long_data:pd.DataFrame,
		wide:pd.DataFrame,
		raw_mode:pd.Series,
		stable_mode:pd.Series,
		change_score:pd.Series,
		change_threshold:float,
	)->None:
		raw_counts=raw_mode.value_counts()
		stable_counts=stable_mode.value_counts()
		self.quality_report={
			"raw_rows":len(long_data),
			"entity_count":int(long_data["entity_id"].nunique()),
			"invalid_timestamp_rows":int(long_data["last_changed"].isna().sum()),
			"non_numeric_state_rows":int(long_data["value"].isna().sum()),
			"synchronized_complete_rows":len(wide),
			"raw_mode_counts":{
				name:int(raw_counts.get(name, 0))
				for name in [mode.value for mode in OperatingMode if mode != OperatingMode.GRID_ON]
				+["unknown"]
			},
			"stable_mode_counts":{
				name:int(stable_counts.get(name, 0))
				for name in [mode.value for mode in OperatingMode if mode != OperatingMode.GRID_ON]
				+["unknown"]
			},
			"trained_mode_counts":self.available_modes(),
			"stability_detection":{
				"method":"robust_multisensor_change_decay",
				"change_threshold":change_threshold,
				"change_score_median":float(change_score.median()),
				"change_score_p95":float(change_score.quantile(0.95)),
				"abrupt_change_rows":int((change_score>change_threshold).sum()),
				"rejected_or_transition_rows":int((stable_mode == "unknown").sum()),
			},
			"power_balance_residuals":{
				mode_name:{
					name:{
						"mean":float(np.mean(model.power_residuals[:, index])),
						"std":float(np.std(model.power_residuals[:, index], ddof=1)),
						"p01":float(np.quantile(model.power_residuals[:, index], 0.01)),
						"median":float(np.quantile(model.power_residuals[:, index], 0.50)),
						"p99":float(np.quantile(model.power_residuals[:, index], 0.99)),
					}
					for index, name in enumerate(model.power_residual_names)
				}
				for mode_name, model in self.regime_models.items()
			},
			"first_timestamp":str(wide.index.min()),
			"last_timestamp":str(wide.index.max()),
			"grid_voltage_min_v":float(wide[list(GRID_VOLTAGE_SENSORS)].min().min()),
			"grid_voltage_max_v":float(wide[list(GRID_VOLTAGE_SENSORS)].max().max()),
		}

	def _validate_fitted_model(self)->None:
		leaked=set(self.feature_columns)&EXCLUDED_OUTPUT_SENSORS
		if leaked:
			raise DataQualityError("Wykluczone sensory w wyjściu: "+", ".join(sorted(leaked)))
		if not self.regime_models:
			raise DataQualityError("Nie znaleziono żadnego stabilnego reżimu z wystarczającymi danymi")
		for name, model in self.regime_models.items():
			if model.training_samples<self.config.minimum_training_samples:
				raise DataQualityError(f"Za mało próbek dla {name}")
			if model.residuals.size == 0:
				raise DataQualityError(f"Brak reszt modelu dla {name}")

	def _require_fitted(self)->None:
		if not self.is_fitted and not self.regime_models:
			raise DeyeModelError("Model nie został wytrenowany")


ModelDeye=DeyeModel


def _build_parser()->argparse.ArgumentParser:
	parser=argparse.ArgumentParser(description="Generatywny symulator falownika Deye")
	subparsers=parser.add_subparsers(dest="command", required=True)
	fit=subparsers.add_parser("fit", help="Wytrenuj i zapisz model")
	fit.add_argument("--csv", nargs="+", required=True, help="Pliki CSV lub katalogi")
	fit.add_argument("--model", type=Path, required=True, help="Docelowy plik modelu")
	fit.add_argument("--summary", action="store_true")
	generate=subparsers.add_parser("generate", help="Generuj bez dostępu do CSV")
	generate.add_argument("--model", type=Path, required=True)
	generate.add_argument("--mode", action="append", required=True)
	generate.add_argument("--samples-per-mode", type=int, default=100)
	generate.add_argument("--random-state", type=int, default=42)
	generate.add_argument("--output", type=Path, required=True)
	inspect=subparsers.add_parser("inspect", help="Pokaż podsumowanie zapisanego modelu")
	inspect.add_argument("--model", type=Path, required=True)
	return parser


def main(argv:Sequence[str] | None=None)->int:
	args=_build_parser().parse_args(argv)
	if args.command == "fit":
		model=DeyeModel.from_csv_files(args.csv)
		model.save(args.model)
		if args.summary:
			print(json.dumps(model.summary(), ensure_ascii=False, indent=2))
		print(f"Zapisano model do {args.model}")
		return 0
	if args.command == "generate":
		model=DeyeModel.load(args.model)
		generated=model.save_generated(
			args.output,
			args.mode,
			samples_per_mode=args.samples_per_mode,
			random_state=args.random_state,
		)
		print(f"Zapisano {len(generated)} próbek do {args.output}")
		return 0
	model=DeyeModel.load(args.model)
	print(json.dumps(model.summary(), ensure_ascii=False, indent=2))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
