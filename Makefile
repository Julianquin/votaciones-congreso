# Atajos. Detalle en docs/ARCHITECTURE.md.
#
# PY apunta al entorno unico de ~/proyectos. En otra maquina: make PY=python ...
PY  ?= ../.venv/bin/python
MES ?=
MOD := $(PY) -m src.votaciones

.PHONY: ayuda test lint check sondear informe mensual

ayuda:
	@echo "Ligeros:  test  lint  check  informe [MES=AAAA-MM]"
	@echo "Red:      sondear (1 peticion)  mensual [MES=AAAA-MM] (~200-300 peticiones)"
	@echo "Carga inicial: $(MOD) historico --desde 2023-09   (lo lanza el usuario; ~1 h)"

test:
	$(PY) -m pytest -q -W error

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

check: lint test

sondear:
	$(MOD) sondear

informe:
	$(MOD) informe $(if $(MES),--mes $(MES))

mensual:
	$(MOD) mensual $(if $(MES),--mes $(MES))
