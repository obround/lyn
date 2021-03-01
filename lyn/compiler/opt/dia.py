from compiler.opt.manager import BlockPass
import compiler.ir as ir


class DIA(BlockPass):
    """
    The dead instruction elimination pass. It runs on every basic block, removing unused/dead
    instructions, but not necessarily all dead code.
    """

    def run_pass(self, block):
        def remove_dead_instrs(instrs):
            # Recursively removes dead instructions. Once every instruction passed to this function
            # is removed, the variables that were used by the instruction may become unused/dead;
            # Therefore, we try to remove all of the used variables as well
            for instr in instrs:
                used_vars = instr.used_vars
                # We don't do `block.remove_instr(instr)`, because when we recursively call this
                # function, the dead instructions list may not be from the same basic block (which
                # should raise an error)
                instr.block.remove_instr(instr)
                # We no longer have to make sure that `x` is of type `AssignmentInstruction` because
                # all used variables are assignment instructions
                remove_dead_instrs(
                    x for x in used_vars if not isinstance(x, ir.Call) and not x.is_used
                )

        remove_dead_instrs(
            instr
            for instr in block.instrs
            if (
                isinstance(instr, ir.AssignmentInstruction)
                and not isinstance(instr, ir.Call)
                and not instr.is_used
            )
        )
