import compiler.ir as ir


class RegAlloc:
    def __init__(self, module, regs):
        assert isinstance(module, ir.Module)
        assert regs, "the registers must not be empty"
        self.module = module
        self.regs = regs
        self.reg_count = len(self.regs)

    def allocate(self):
        for subroutine in self.module.subroutines:
            self.build_intervals(subroutine)

    def build_intervals(self, subroutine):
        for block in subroutine.blocks:
            pass
