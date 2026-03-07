"""
Plugin de ejemplo para Genesis.

Este archivo muestra como crear un plugin.
Puedes copiar este archivo y modificarlo para crear tus propios plugins.

Los plugins se cargan automaticamente desde la carpeta plugins/
"""

PLUGIN_NAME = "Ejemplo"
PLUGIN_VERSION = "1.0"
PLUGIN_DESCRIPTION = "Plugin de ejemplo que muestra la estructura basica"


def on_load(genesis):
    """Se llama cuando el plugin se carga. Recibe la instancia de Genesis."""
    # Puedes acceder a cualquier subsistema:
    # genesis.brain, genesis.memory, genesis.evolution, etc.
    pass


def on_unload(genesis):
    """Se llama cuando el plugin se descarga."""
    pass


def register_commands():
    """
    Registra comandos nuevos.
    Retorna un dict: {"/comando": {"handler": funcion, "help": "descripcion"}}
    """
    return {
        "/hello": {
            "handler": cmd_hello,
            "help": "Saludo del plugin de ejemplo",
        },
        "/dice": {
            "handler": cmd_dice,
            "help": "Lanza un dado de N caras",
        },
    }


def cmd_hello(genesis, args: str) -> str:
    """Handler del comando /hello."""
    gen = genesis.evolution.get_generation()
    n_memories = len(genesis.memory.long_term.memories)
    return (
        f"Hola desde el plugin de ejemplo!\n"
        f"  Genesis Gen {gen} con {n_memories} memorias.\n"
        f"  Este plugin demuestra como extender Genesis sin tocar el core."
    )


def cmd_dice(genesis, args: str) -> str:
    """Handler del comando /dice — lanza un dado."""
    import random
    try:
        sides = int(args) if args else 6
    except ValueError:
        sides = 6
    result = random.randint(1, sides)
    return f"Dado de {sides} caras: {result}"


def on_message(genesis, user_input: str, response: str):
    """
    Hook que se ejecuta despues de cada interaccion.
    Util para logging, analytics, o triggers automaticos.
    """
    # Ejemplo: contar palabras por interaccion
    # (En un plugin real, podrias guardar stats, triggers, etc.)
    pass
