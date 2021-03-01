from contextlib import contextmanager


class PrettyPrinter:
    """Simple pretty printer with indentation and automatic dedentation capabilities"""

    def __init__(self):
        self._data = ""
        self._indentation = ""

    def __str__(self):
        return self._data

    def append(self, *data):
        """Adds data to the pretty printed output"""
        self._data += self._indentation
        self._data += "".join(data)

    def appendln(self, *data):
        """Adds data to the pretty printed output with a newline after it"""
        self.append(*data, "\n")

    @contextmanager
    def indent(self):
        """Adds an indentation of four to its scope.

        Example:
            with pp.indent():
                # Everything from now on to the end of `PrettyPrinter.indent`'s scope
                # will be indented four spaces
            ...
        """
        old_indentation = self._indentation
        try:
            self._indentation += "    "
            yield
        finally:
            self._indentation = old_indentation
