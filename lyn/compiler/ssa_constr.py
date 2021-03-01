from dataclasses import dataclass
import compiler.ir as ir
import collections


@dataclass
class SSADef:
    """A definition of a variable in SSA form, holding the next variable number
    `count`, and the current definition of the variable, `current_def`
    """

    def __init__(self, count, current_def):
        self.count = count
        self.current_def = current_def


class SSA:
    """
    Helps convert a program into pruned SSA form in linear time. This algorithm is
    especially useful in SSA reconstruction
    """

    def __init__(self):
        self.variables = {}
        self.incomplete_phis = collections.defaultdict(dict)
        self.sealed_blocks = set()

    def new_variable(self, instr, block):
        """
        Registers a new variable. It returns `instr` back to facilitate on the fly
        SSA building
        """
        assert isinstance(instr, ir.AssignmentInstruction)
        if instr.name not in self.variables:
            self.variables[instr.name] = SSADef(0, {block.name: instr})
            instr.ssa_id = 0
        else:
            ssa_def = self.variables[instr.name]
            ssa_def.count += 1
            instr.ssa_id = ssa_def.count
            ssa_def.current_def[block.name] = instr
        return instr

    def get_reaching_def(self, variable, block):
        """Looks for the reaching definition of a variable in a basic block"""
        if block.name in self.variables[variable].current_def:
            return self.variables[variable].current_def[block.name]
        return self.get_reaching_def_recursive(variable, block)

    def get_reaching_def_recursive(self, variable, block):
        """
        Recursively looks for the reaching definition of a variable in a basic block.
        This method shouldn't be used directly (with the exception of testing)
        """
        if block.name not in self.sealed_blocks:
            # Handle an incomplete CFG by inserting a phi function that will later be
            # scrutinized by `SSA.add_sealed_block`
            phi = ir.Phi(variable, ir.Type.VOID)
            block.add_phi_instr(phi)
            self.new_variable(phi, block)
            self.incomplete_phis[block.name][variable] = phi
            return phi
        elif len(block.preds) == 1:
            # If there is only one predecessor, we don't need to insert an phi function
            # because the reaching definition will be in the predecessor
            return self.get_reaching_def(variable, block.preds[0])
        else:
            # Insert an operandless phi function to prevent endless recursion that may
            # happen when adding operands to the phi function (call `SSA.add_phi_operands`)
            # TODO: Implement the marker algorithm
            phi = ir.Phi(variable, ir.Type.VOID)
            phi.ssa_id = self.variables[variable].count
            block.add_phi_instr(phi)
            self.new_variable(phi, block)
            return self.add_phi_operands(variable, phi)

    def add_phi_operands(self, variable, phi):
        """
        Adds operands to a phi function be looking for the reaching definition in the
        phi function's block's predecessors. Afterwards, it checks if it is redundant by
        calling `SSA.remove_trivial_phi`
        """
        for pred in phi.block.preds:
            phi.add_input(self.get_reaching_def(variable, pred))
        return self.remove_trivial_phi(phi)

    def remove_trivial_phi(self, phi):
        """Checks whether a phi function is redundant"""
        same = None
        for param in phi.inputs:
            if param == same or param == phi:
                # The param is unique or a self-reference
                continue
            if same is not None:
                # The phi combines at least two values: non-trivial
                return phi
            same = param
        # The phi function is trivial
        phi.block.phis.remove(phi)
        users = [x for x in phi.users if x is not phi]
        phi.replace_by(same)
        # Replace every reference to the phi in the current def
        for block, instr in self.variables[phi.name].current_def.items():
            if instr is phi:
                self.variables[phi.name].current_def[block] = same
        # Attempts to recursively remove all phi users which may have become trivial
        # after referring to a this phi function (which is now trivial)
        for use in users:
            if isinstance(use, ir.Phi):
                self.remove_trivial_phi(use)
        return same

    def add_sealed_block(self, block):
        """
        Seals a given basic block and adds operands/deems trivial any incomplete phi
        functions in the block
        """
        for variable in self.incomplete_phis[block.name]:
            self.add_phi_operands(variable, self.incomplete_phis[block.name][variable])
        self.sealed_blocks.add(block.name)
