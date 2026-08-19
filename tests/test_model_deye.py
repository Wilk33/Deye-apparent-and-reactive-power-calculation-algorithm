from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from deye_power_calculation.model_deye import (
	EXCLUDED_OUTPUT_SENSORS,
	DeyeModel,
	InterventionUnavailableError,
	OperatingMode,
	UnsupportedModeError,
)


def _write_measurements(path:Path, include_grid_off:bool=True)->None:
	start=pd.Timestamp("2026-01-01T00:00:00Z")
	rows=[]
	index=0

	def add_run(mode:str, count:int)->None:
		nonlocal index
		for local in range(count):
			timestamp=start+pd.Timedelta(seconds=5*index)
			wave=np.sin(local/11.0)
			if mode == "grid_on_import":
				grid_voltage=230.0+1.2*wave
				grid_phase_power=300.0+35.0*wave
				pv=2400.0+180.0*wave
				battery=-700.0+90.0*wave
			elif mode == "grid_on_export":
				grid_voltage=231.0+1.0*wave
				grid_phase_power=-400.0+45.0*wave
				pv=5200.0+250.0*wave
				battery=600.0+80.0*wave
			elif mode == "grid_on_idle":
				grid_voltage=229.0+0.8*wave
				grid_phase_power=10.0+15.0*wave
				pv=1600.0+120.0*wave
				battery=-300.0+50.0*wave
			elif mode == "grid_off":
				grid_voltage=0.0
				grid_phase_power=0.0
				pv=2800.0+150.0*wave
				battery=-1200.0+80.0*wave
			else:
				grid_voltage=100.0
				grid_phase_power=0.0
				pv=0.0
				battery=0.0
			values={
				"sensor.deye_pv_power":pv,
				"sensor.deye_battery_power":battery,
				"sensor.deye_q_prime_total_reactive_power":9999.0,
			}
			for phase_index, phase in enumerate(("l1", "l2", "l3"), start=1):
				phase_wave=np.sin(local/11.0+phase_index/5.0)
				grid_value=grid_phase_power+phase_index
				inverter_value=850.0+30.0*phase_wave
				balance_error=1.5*np.sin(local/7.0+phase_index)
				values.update(
					{
						f"sensor.deye_grid_{phase}_voltage":grid_voltage+0.2*phase_index,
						f"sensor.deye_grid_{phase}_current":abs(grid_phase_power)/230.0+0.5,
						f"sensor.deye_grid_{phase}_power":grid_value,
						f"sensor.deye_diag_inverter_{phase}_voltage":230.0+phase_wave,
						f"sensor.deye_inverter_{phase}_current":2.0+0.2*phase_wave,
						f"sensor.deye_inverter_{phase}_power":inverter_value,
						f"sensor.deye_load_{phase}_voltage":230.0+0.5*phase_wave,
						f"sensor.deye_load_{phase}_power":(
							grid_value+inverter_value+balance_error
						),
					}
				)
			for prefix in ("grid", "inverter", "load"):
				phase_total=sum(
					values[f"sensor.deye_{prefix}_{phase}_power"]
					for phase in ("l1", "l2", "l3")
				)
				values[f"sensor.deye_{prefix}_power"]=phase_total+0.8*np.sin(
					local/9.0+len(prefix)
				)
			for entity_id, value in values.items():
				rows.append(
					{
						"entity_id":entity_id,
						"state":value,
						"last_changed":timestamp.isoformat(),
					}
				)
			index+=1

	def add_transition()->None:
		add_run("transition", 10)

	add_run("grid_on_import", 140)
	add_transition()
	add_run("grid_on_export", 140)
	add_transition()
	add_run("grid_on_idle", 140)
	if include_grid_off:
		add_transition()
		add_run("grid_off", 140)
	pd.DataFrame(rows).to_csv(path, index=False)


@pytest.fixture
def fitted_model(tmp_path:Path)->DeyeModel:
	csv_path=tmp_path/"measurements.csv"
	_write_measurements(csv_path)
	return DeyeModel.from_csv_files(csv_path)


def test_training_only_and_excluded_sensors_are_not_generated(fitted_model:DeyeModel)->None:
	generated=fitted_model.generate("grid_on_import", random_state=1)
	assert not set(generated.columns)&EXCLUDED_OUTPUT_SENSORS
	assert "sensor.deye_pv_power" not in generated.columns
	assert "sensor.deye_battery_power" not in generated.columns


def test_combined_modes_generate_one_hundred_each(fitted_model:DeyeModel)->None:
	generated=fitted_model.generate(
		"grid_on_import + grid_on_export",
		samples_per_mode=100,
		random_state=42,
	)
	assert len(generated) == 200
	assert generated["operating_mode"].value_counts().to_dict() == {
		"grid_on_import":100,
		"grid_on_export":100,
	}
	assert generated[fitted_model.feature_columns].notna().all().all()


def test_saved_model_generates_without_csv(fitted_model:DeyeModel, tmp_path:Path)->None:
	model_path=tmp_path/"deye.pkl"
	fitted_model.save(model_path)
	loaded=DeyeModel.load(model_path)
	generated=loaded.generate("grid_on_idle", random_state=7)
	assert len(generated) == 100
	assert set(generated["operating_mode"]) == {"grid_on_idle"}


def test_generation_is_deterministic_after_loading(
	fitted_model:DeyeModel,
	tmp_path:Path,
)->None:
	model_path=tmp_path/"deye.pkl"
	fitted_model.save(model_path)
	loaded=DeyeModel.load(model_path)
	first=loaded.generate("grid_on", random_state=9)
	second=loaded.generate("grid_on", random_state=9)
	pd.testing.assert_frame_equal(first, second)


def test_grid_off_requires_real_training_examples(tmp_path:Path)->None:
	csv_path=tmp_path/"grid_on_only.csv"
	_write_measurements(csv_path, include_grid_off=False)
	model=DeyeModel.from_csv_files(csv_path)
	with pytest.raises(UnsupportedModeError, match="nie występuje"):
		model.generate(OperatingMode.GRID_OFF)


def test_generated_values_stay_inside_learned_bounds(fitted_model:DeyeModel)->None:
	generated=fitted_model.generate("grid_on_export", random_state=4)
	regime=fitted_model.regime_models[OperatingMode.GRID_ON_EXPORT.value]
	lower=regime.center+regime.lower*regime.scale
	upper=regime.center+regime.upper*regime.scale
	derived={
		"sensor.deye_grid_power",
		"sensor.deye_inverter_power",
		"sensor.deye_load_power",
		"sensor.deye_load_l1_power",
		"sensor.deye_load_l2_power",
		"sensor.deye_load_l3_power",
	}
	indices=[
		index
		for index, name in enumerate(fitted_model.feature_columns)
		if name not in derived
	]
	values=generated[[fitted_model.feature_columns[index] for index in indices]].to_numpy()
	assert np.all(values>=lower[indices]-1e-9)
	assert np.all(values<=upper[indices]+1e-9)


def test_generated_active_power_balance_preserves_empirical_error(
	fitted_model:DeyeModel,
)->None:
	generated=fitted_model.generate("grid_on", random_state=22)
	for phase in ("l1", "l2", "l3"):
		load=generated[f"sensor.deye_load_{phase}_power"]
		grid=generated[f"sensor.deye_grid_{phase}_power"]
		inverter=generated[f"sensor.deye_inverter_{phase}_power"]
		error=load-grid-inverter
		assert not np.allclose(error, 0.0)
		assert error.abs().max()<2.0
	for prefix in ("grid", "inverter", "load"):
		total=generated[f"sensor.deye_{prefix}_power"]
		phases=sum(
			generated[f"sensor.deye_{prefix}_{phase}_power"]
			for phase in ("l1", "l2", "l3")
		)
		error=total-phases
		assert not np.allclose(error, 0.0)
		assert error.abs().max()<1.0


def test_active_load_refuses_to_invent_response_without_kettle_pairs(
	fitted_model:DeyeModel,
)->None:
	state=fitted_model.generate("grid_on_idle", random_state=3).iloc[0]
	with pytest.raises(InterventionUnavailableError, match="czajnik"):
		fitted_model.apply_active_load(state, 2000.0, "L1", "grid_on_idle")


def test_kettle_csv_is_not_mixed_into_base_training(tmp_path:Path)->None:
	base=tmp_path/"history.csv"
	kettle=tmp_path/"czajnik1.csv"
	_write_measurements(base)
	_write_measurements(kettle)
	model=DeyeModel.from_csv_files(tmp_path)
	assert model.source_files == [str(base.resolve())]
	assert model.intervention_source_files == [str(kettle.resolve())]
	assert model.summary()["active_load_intervention"]["available"] is False


def test_stability_detection_is_based_on_multisensor_change(
	fitted_model:DeyeModel,
)->None:
	quality=fitted_model.summary()["quality"]["stability_detection"]
	assert quality["method"] == "robust_multisensor_change_decay"
	assert quality["change_threshold"]>0.0
	assert quality["abrupt_change_rows"]>0
	assert quality["rejected_or_transition_rows"]>0


def test_generated_grid_flow_matches_requested_mode(fitted_model:DeyeModel)->None:
	generated=fitted_model.generate(
		"grid_on_import + grid_on_export",
		random_state=12,
	)
	phase_power=[
		"sensor.deye_grid_l1_power",
		"sensor.deye_grid_l2_power",
		"sensor.deye_grid_l3_power",
	]
	grid_sum=generated[phase_power].sum(axis=1)
	import_rows=generated["operating_mode"] == "grid_on_import"
	export_rows=generated["operating_mode"] == "grid_on_export"
	assert (grid_sum[import_rows]>150.0).all()
	assert (grid_sum[export_rows]<-150.0).all()


def test_less_than_one_hundred_samples_is_rejected(fitted_model:DeyeModel)->None:
	with pytest.raises(ValueError, match="co najmniej 100"):
		fitted_model.generate("grid_on", samples_per_mode=99)
