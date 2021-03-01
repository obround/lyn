import operator
import compiler.ir as ir
from compiler.opt.manager import BlockPass
from compiler.opt.dia import DIA


def wrapper(func):
    """
    Returns a lambda which applies the constant folding function, and then corrects
    bits to wrap it (in the case it overflowed)
    """
    return lambda x, y, bits, signed: wrap(func(x, y), bits, signed)


def wrap(value, bits, signed):
    """Wraps a value to a given amount of bits"""
    base = 1 << bits
    value %= base
    return value - base if signed and value.bit_length() == bits else value


def fold_instr(instr):
    """
    Folds an instruction. The criteria to fold is:
        1. It must be a binary operation
        2. It's operation mut be foldable
        3. Its parameters must be constants which have a specified amount of bits
    """
    if (
        isinstance(instr, ir.BinOp)
        and instr.op in ops
        and all(
            isinstance(param, ir.Const) and param.instr_type.bits
            for param in (instr.x, instr.y)
        )
    ):
        folded = ops[instr.op](
            int(instr.x.value),
            int(instr.y.value),
            instr.instr_type.bits,
            instr.instr_type.is_signed,
        )
        new_instr = ir.Const(instr.name, instr.instr_type, str(folded))
        new_instr.ssa_id = instr.ssa_id
        return new_instr


ops = {
    ir.Op.ADD: wrapper(operator.add),
    ir.Op.SUB: wrapper(operator.sub),
    ir.Op.MUL: wrapper(operator.mul),
    ir.Op.MOD: wrapper(operator.mod),
    ir.Op.LSH: wrapper(operator.lshift),
    ir.Op.RSH: wrapper(operator.rshift),
}


class Value:
    def __init__(self, opcode_name, is_commutative, instr_type, params):
        self.opcode_name = opcode_name
        self.instr_type = instr_type
        # If the operation is commutative, sort it by converting every item to a string
        self.params = params if not is_commutative else sorted(params, key=str)

    def __eq__(self, other):
        return (
            isinstance(other, Value)
            and self.opcode_name == other.opcode_name
            and self.instr_type == other.instr_type
            and self.params == other.params
        )

    def __hash__(self):
        return hash((self.opcode_name, self.instr_type, *self.params))

    def lookup_in(self, value_table):
        """Returns the value in the given value table"""
        return value_table.get(self)


class LVN(BlockPass):
    """
    The local value numbering optimization pass. It runs on every basic block, removing common
    subexpressions, simultaneously propagating copies and constants
    """

    def __init__(self):
        self.num_count = -1
        self.dia = DIA()

    def _fresh_num(self):
        self.num_count += 1
        return self.num_count

    def run_pass(self, block):
        numberings = {}
        value_table = {}
        name = {}
        as_name = lambda x: (x.name, x.ssa_id)

        for instr in block.instrs:
            if isinstance(instr, ir.AssignmentInstruction):
                folded = fold_instr(instr)
                if folded:
                    # The instruction can be folded into a constant
                    instr.block.replace_instr(instr, folded)
                    instr = folded
                value = Value(
                    instr.opcode_name,
                    instr.instr_type,
                    isinstance(instr, ir.BinOp) and instr.op.is_commutative(),
                    [
                        numberings[as_name(x)]
                        # If the operand is a constant, the operand will be a string
                        if isinstance(x, ir.AssignmentInstruction)
                        and not isinstance(x, ir.Call)
                        else x
                        for x in instr.operands
                    ],
                )
                number = value.lookup_in(value_table)
                if number:
                    # An identical instruction already exists, so we will replace it with
                    # a copy instruction
                    new_instr = ir.Id(instr.name, instr.instr_type, name[number])
                    new_instr.ssa_id = instr.ssa_id
                    block.replace_instr(instr, new_instr)
                else:
                    # The instruction is unique (in this block at least), so we can register
                    # it under a number
                    number = self._fresh_num()
                    value_table[value] = number
                    name[number] = instr
                    # Try to replace every operand with it's redirection
                    for i, param in enumerate(instr.operands):
                        if isinstance(param, ir.AssignmentInstruction):
                            new_instr = name[numberings[as_name(param)]]
                            instr.set_operand_at(i, new_instr)
                numberings[as_name(instr)] = number
        # Run the dead instruction pass to clean up
        self.dia.run_pass(block)
