class Pass:
    """Base class for all passes"""

    def run_pass(self, item):
        raise NotImplementedError()


class ModulePass(Pass):
    pass


class FunctionPass(Pass):
    pass


class BlockPass(Pass):
    pass


class InstructionPass(Pass):
    pass


class PassManager:
    """A pass manager that attempts to efficiently run all registered passes"""

    def __init__(self):
        self._module_passes = []
        self._function_passes = []
        self._basic_block_passes = []
        self._instruction_passes = []

    def register_pass(self, p):
        """Adds a new pass to the list of passes to be run on a module"""
        assert issubclass(p, Pass), "pass `{}` does not inherit from any of the pass superclasses".format(p.__name__)
        if isinstance(p, ModulePass):
            self._module_passes.append(p)
        elif isinstance(p, FunctionPass):
            self._function_passes.append(p)
        elif isinstance(p, BlockPass):
            self._basic_block_passes.append(p)
        elif isinstance(p, InstructionPass):
            self._instruction_passes.append(p)

    def run_passes(self, module):
        """
        Runs all the passes registered in the manager. The passes run in this order:
            1. Module passes
            2. Function passes
            3. Block passes
            4. Instruction passes
        """
        for mpass in self._module_passes:
            mpass(module)
        for function in module.functions:
            for fpass in self._function_passes:
                fpass(function)
            for block in function.blocks:
                for bpass in self._basic_block_passes:
                    bpass(block)
                for instr in block.instrs:
                    for ipass in self._instruction_passes:
                        ipass(instr)
