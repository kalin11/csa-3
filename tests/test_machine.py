import contextlib
import io
import logging
import os
import tempfile

import pytest
from lab3.interpreter import translator
from lab3.machine import virtual_machine


@pytest.mark.golden_test("golden/*.yml")
def test_translator_and_machine(golden, caplog):
    caplog.set_level(logging.DEBUG)

    with tempfile.TemporaryDirectory() as tmpdirname:
        source = os.path.join(tmpdirname, "source.vjs")
        input_stream = os.path.join(tmpdirname, "input.txt")
        target = os.path.join(tmpdirname, "target.o")
        static_mem = os.path.join(tmpdirname, "static_mem.o")

        with open(source, "w", encoding="utf-8") as file:
            file.write(golden["in_source"])
        with open(input_stream, "w", encoding="utf-8") as file:
            file.write(golden["in_stdin"])
        with open(static_mem, "w", encoding="utf-8") as file:
            file.write(golden["static_mem"])

        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            translator.main(source, target, static_mem)
            print("============================================================")
            virtual_machine.main(target, input_stream, static_mem)

        with open(target, encoding="utf-8") as file:
            code = file.read()

        assert code == golden.out["out_code"]
        assert stdout.getvalue() == golden.out["out_stdout"]
        assert caplog.text == golden.out["out_log"]
