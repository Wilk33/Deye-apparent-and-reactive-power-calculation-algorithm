"""Obliczanie mocy pozornej i biernej dla danych falownika Deye."""

__version__="0.1.0"

__all__=[
	"DeyeModel",
	"InterventionUnavailableError",
	"ModelConfig",
	"OperatingMode",
	"__version__",
]


def __getattr__(name:str):
	if name in {
		"DeyeModel",
		"InterventionUnavailableError",
		"ModelConfig",
		"OperatingMode",
	}:
		from deye_power_calculation import model_deye

		return getattr(model_deye, name)
	raise AttributeError(name)
