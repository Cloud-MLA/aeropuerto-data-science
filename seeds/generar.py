"""CLI para generar la data ficticia del proyecto.

Uso:
    python generar.py            # genera los 3 microservicios en orden
    python generar.py --ms 2     # solo MS2
    python generar.py --ms 1     # solo MS1 (requiere MS2 previo)
    python generar.py --ms 3     # solo MS3 (requiere MS2 previo)
"""
import argparse
import random
import sys

from faker import Faker

import config
from generators import ms1_pasajeros, ms2_vuelos


def preparar_directorios() -> None:
    for d in (config.OUTPUT_MS1, config.OUTPUT_MS2, config.OUTPUT_MS3):
        d.mkdir(parents=True, exist_ok=True)


def _seeds_deterministas() -> tuple[random.Random, Faker]:
    """Prepara un RNG y un Faker con el SEED fijo (reproducible byte-a-byte)."""
    rng = random.Random(config.SEED)
    faker = Faker("es_ES")
    Faker.seed(config.SEED)
    return rng, faker


def generar_ms2() -> dict:
    rng, faker = _seeds_deterministas()
    return ms2_vuelos.generar(rng, faker)


def generar_ms1() -> dict:
    rng, faker = _seeds_deterministas()
    return ms1_pasajeros.generar(rng, faker)


def generar_ms3() -> None:
    print("[MS3] generador aun no implementado (llega en el proximo PR)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generador de seeds del aeropuerto")
    parser.add_argument(
        "--ms",
        type=int,
        choices=[1, 2, 3],
        help="Generar solo un microservicio (por defecto: los 3 en orden MS2->MS1->MS3)",
    )
    args = parser.parse_args()

    preparar_directorios()
    print(f"SEED = {config.SEED}")
    print(f"Salida: {config.OUTPUT_DIR}")

    if args.ms is None:
        generar_ms2()
        generar_ms1()
        generar_ms3()
    elif args.ms == 2:
        generar_ms2()
    elif args.ms == 1:
        generar_ms1()
    elif args.ms == 3:
        generar_ms3()

    return 0


if __name__ == "__main__":
    sys.exit(main())
