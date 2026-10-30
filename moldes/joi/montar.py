#!/usr/bin/env python3
"""Invólucro do molde joi: o montador é um só, o montar.py da raiz do produto (veja o uso lá). Continua aqui para quem chama o caminho antigo e para o portão, que importa o montar.py ao lado do molde."""
import importlib.util as _u, os as _o, sys as _s; _s.dont_write_bytecode = True; _e = _u.spec_from_file_location("montador", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "..", "..", "montar.py")); _m = _u.module_from_spec(_e); _e.loader.exec_module(_m)
globals().update(_m.api("joi"))
if __name__ == "__main__": _m.main(_s.argv[1:], molde="joi")
