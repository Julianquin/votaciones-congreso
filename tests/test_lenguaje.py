import pytest

from src.votaciones.lenguaje import de, titulo_llano


@pytest.mark.parametrize(
    ("oficial", "llano"),
    [
        ("Moción consecuencia de interpelación urgente del Grupo Parlamentario VOX, sobre la "
         "política energética.", "Moción de Vox sobre la política energética"),
        ("Moción consecuencia de interpelación urgente del Grupo Parlamentario Mixto (Sra. "
         "Belarra Urteaga), relativa a la vivienda.",
         "Moción del Grupo Mixto relativa a la vivienda"),
        ("Proposición no de Ley del Grupo Parlamentario Popular en el Congreso, para ajustar el "
         "IRPF por la inflación.", "Propuesta del PP para ajustar el IRPF por la inflación"),
        ("Real Decreto-ley 9/2026, de 3 de marzo, de medidas urgentes en materia de transporte.",
         "Decreto-ley 9/2026 del Gobierno, de medidas urgentes en materia de transporte"),
        ("Votación de la enmienda a la totalidad de devolución al Proyecto de Ley de Costas, "
         "presentada por el Grupo Parlamentario VOX.",
         "Enmienda de Vox para devolver el Proyecto de Ley de Costas"),
        ("Solicitud de los Grupos Parlamentarios Socialista y Plurinacional SUMAR, de creación de "
         "una Comisión de Investigación.",
         "Solicitud de PSOE y Sumar, de creación de una Comisión de Investigación"),
        ("Del Grupo Parlamentario Popular en el Congreso, en defensa del campo. Se vota en sus "
         "términos.", "Propuesta del PP en defensa del campo"),
        # Lo que no es fórmula se deja tal cual.
        ("Acuerdo entre el Reino de España y Brasil sobre transporte aéreo.",
         "Acuerdo entre el Reino de España y Brasil sobre transporte aéreo"),
    ],
)  # fmt: skip
def test_titulo_llano(oficial, llano):
    assert titulo_llano(oficial) == llano


def test_titulo_llano_recorta():
    t = titulo_llano("Proyecto de Ley " + "muy " * 80 + "larga.", 60)
    assert len(t) == 60 and t.endswith("…")


def test_articulo():
    assert (
        de("PP") == "del PP" and de("Vox") == "de Vox" and de("PSOE y Sumar") == "del PSOE y Sumar"
    )
