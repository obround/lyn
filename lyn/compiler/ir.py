from enum import Enum
from compiler.pretty import PrettyPrinter


class Binding(Enum):
    """The binding of something (locally or globally bound)"""

    LOCAL = 0
    GLOBAL = 1

    def __str__(self):
        return "%" if self == Binding.LOCAL else "@"


class Op(Enum):
    """The operation of a `BinOp`"""

    ADD = 0
    SUB = 1
    MUL = 2
    DIV = 3
    MOD = 4
    LSH = 5
    RSH = 6
    LT = 7
    GT = 8
    LE = 9
    GE = 10
    EQ = 11
    NQ = 12

    def __str__(self):
        return self.name.lower()

    def is_commutative(self):
        return self in (Op.ADD, Op.MUL, Op.EQ)


class Type(Enum):
    """A type, holding the number of bits and the signed status"""

    I1 = 0, 1, False
    I8 = 1, 8, False
    I16 = 2, 16, False
    I32 = 3, 32, False
    I64 = 4, 64, False
    I128 = 5, 128, False
    I256 = 6, 256, False
    U8 = 7, 8, True
    U16 = 8, 16, True
    U32 = 9, 32, True
    U64 = 10, 64, True
    U128 = 11, 128, True
    U256 = 12, 256, True
    F32 = 13, 32, False
    F64 = 14, 64, False
    STRING = 15, None, False
    VOID = 16, None, False

    def __init__(self, type_id, bits, is_signed):
        self.type_id = type_id
        self.bits = bits
        self.is_signed = is_signed
        self.is_unsigned = not is_signed

    def __str__(self):
        return self.name.lower()

    @property
    def is_int(self):
        return self.value not in (Type.F32, Type.F64, Type.STRING, Type.VOID)


class Parameter:
    """A parameter to be passed to a subroutine. It represents `(str, type)`"""

    def __init__(self, name, param_type):
        assert isinstance(param_type, Type)
        self.name = name
        self.param_type = param_type

    def __eq__(self, other):
        return (
            isinstance(other, Parameter)
            and self.name == other.name
            and self.param_type == other.param_type
        )

    def __hash__(self):
        return hash((self.name, self.param_type))

    def __str__(self):
        return "%{}: {}".format(self.name, self.param_type)


class Block:
    """A basic block; It contains no branches except the entry and exit branch"""

    def __init__(self, name):
        self.name = name
        self.subroutine = None
        self._instrs = []
        self._phis = []
        self._preds = []
        self._succs = []

    def __eq__(self, other):
        return (
            isinstance(other, Block)
            and self.name == other.name
            and self.instrs == other.instrs
            and self.phis == other.phis
        )

    def __hash__(self):
        return hash((self.name, self.instrs, self.phis))

    def __str__(self):
        pretty = PrettyPrinter()
        pretty.appendln(".{}:".format(self.name))
        with pretty.indent():
            for phi in self.phis:
                pretty.appendln(str(phi))
            for instr in self.instrs:
                pretty.appendln(str(instr))
        return str(pretty)

    def add_phi_instr(self, instr):
        """Adds a phi instruction to the basic block. To add a normal instruction, look to `Block.add_instr`"""
        assert isinstance(instr, Phi)
        instr.block = self
        self._phis.append(instr)
        return instr

    def add_instr(self, instr):
        """Adds an instruction to the basic block. To add a phi instruction, look to `Block.add_phi_instr`"""
        assert isinstance(instr, Instruction)
        instr.block = self
        self._instrs.append(instr)
        return instr

    def insert_instr(self, instr, loc):
        """
        Inserts an instruction at a specific point in the basic block. To add a phi instruction, look
        to `Block.add_phi_instr`. Remember that this has a worst case of O(n)
        """
        assert isinstance(instr, Instruction)
        instr.block = self
        self._instrs.insert(loc, instr)
        return instr

    def replace_instr(self, old_instr, new_instr):
        """Replaces an existing instruction with another non-existing instruction"""
        assert isinstance(old_instr, Instruction)
        assert isinstance(new_instr, Instruction)
        assert old_instr in self.instrs, "instruction not in instruction list"
        assert not new_instr.is_used, "the new instruction must not be used"
        assert not new_instr.block, "the new instruction must not be in another block"
        new_instr.block = self
        self._instrs.insert(self.instrs.index(old_instr), new_instr)
        old_instr.replace_by(new_instr)
        self._instrs.remove(old_instr)

    def remove_instr(self, instr):
        """Removes an existing instruction. The instruction must not be used!"""
        assert isinstance(instr, Instruction)
        assert instr in self.instrs, "instruction not in instruction list"
        assert not instr.is_used, "the instruction is used! it is not safe to remove it"
        instr.block = None
        instr.remove_used_vars(*instr.used_vars)
        self._instrs.remove(instr)

    def remove_phi_instr(self, phi):
        """Remove an existing phi instruction. The phi instruction must not be used!"""
        assert isinstance(phi, Phi)
        assert phi in self.phis, "phi instruction not in phi list"
        assert not phi.is_used, "phi is used! it is not safe to remove it"
        phi.block = None
        phi.remove_used_vars(phi.used_vars)
        self._phis.remove(phi)

    def add_pred(self, block):
        """Adds a predecessor to the basic block"""
        assert isinstance(block, Block)
        self._preds.append(block)
        if self not in block.succs:
            block.add_succ(self)

    def add_succ(self, block):
        """Adds a successor to the basic block"""
        assert isinstance(block, Block)
        self._succs.append(block)
        if self not in block.preds:
            block.add_pred(self)

    @property
    def is_empty(self):
        return self.instr_count == 0

    @property
    def instr_count(self):
        return len(self._instrs)

    @property
    def instrs(self):
        return self._instrs

    @property
    def phis(self):
        return self._phis

    @property
    def preds(self):
        return self._preds

    @property
    def succs(self):
        return self._succs


class Module:
    """A container for subroutines"""

    def __init__(self, name):
        self.name = name
        self._subroutines = []

    def __eq__(self, other):
        return (
            isinstance(other, Module)
            and self.name == other.name
            and self.subroutines == other.subroutines
        )

    def __hash__(self):
        return hash((self.name, self.subroutines))

    def __str__(self):
        pretty = PrettyPrinter()
        pretty.appendln("module", " ", self.name)
        pretty.appendln()
        for func in self.subroutines:
            pretty.appendln(str(func))
        return str(pretty)

    def add_subroutine(self, subroutine):
        """Add a subroutine to the module"""
        assert isinstance(subroutine, Subroutine)
        self._subroutines.append(subroutine)

    @property
    def subroutines(self):
        return self._subroutines


class Subroutine:
    """Base class for all subroutines (function and procedures)"""

    def __init__(self, name, params, binding):
        assert all(isinstance(x, Parameter) for x in params)
        assert isinstance(binding, Binding)
        self.name = name
        self.params = params
        self.binding = binding
        self._blocks = {}

    def __eq__(self, other):
        return (
            isinstance(other, Subroutine)
            and self.name == other.name
            and self.params == other.params
            and self.binding == other.binding
            and self.blocks == other.blocks
        )

    def __hash__(self):
        return hash((self.name, *self.params, self.binding, *self._blocks))

    def compare_structure(self, other):
        """
        Similar to `Subroutine.__eq__`, but doesn't compare `Subroutine.name` and
        `Subroutine.binding`, This is because it only compares the structure of
        the subroutines
        """
        return (
            isinstance(other, Subroutine)
            and self.params == other.params
            and self.blocks == other.blocks
        )

    def add_block(self, block):
        """Adds a block to the subroutine"""
        assert isinstance(block, Block)
        assert block.name not in self.blocks, "redefinition of block `{}`".format(
            block.name
        )
        block.parent_func = self
        self._blocks[block.name] = block
        return block

    def add_param(self, param):
        """Adds a parameter to the subroutine"""
        assert isinstance(param, Parameter)
        self.params.append(param)
        return param

    def remove_block(self, block):
        """Removes a block from the subroutine"""
        assert isinstance(block, Block)
        assert block.name in self.blocks, "block {} does not exist".format(block.name)
        del self._blocks[block.name]

    def remove_param(self, param):
        """Removes a parameter from the subroutine"""
        assert isinstance(param, Parameter)
        self.params.remove(param)

    @property
    def blocks(self):
        return self._blocks


class Function(Subroutine):
    """
    A subroutine which returns a value. Look to `Procedure` for a subroutine that
    does not return any value
    """

    def __init__(self, name, params, ret_type, binding):
        super().__init__(name, params, binding)
        assert isinstance(ret_type, Type)
        self.ret_type = ret_type

    def __eq__(self, other):
        return (
            isinstance(other, Function)
            and super().__eq__(other)
            and self.ret_type == other.ret_type
        )

    def __hash__(self):
        return hash((super().__hash__(), self.ret_type))

    def __str__(self):
        return "function {} {}{}({}) {{\n{}}}".format(
            self.ret_type,
            self.binding,
            self.name,
            ", ".join("%" + str(x) for x in self.params),
            "\n".join(map(str, self.blocks.values())),
        )

    def compare_structure(self, other):
        return (
            isinstance(other, Function)
            and super().compare_structure(other)
            and self.ret_type == other.ret_type
        )


class Procedure(Subroutine):
    """
    A subroutine which doesn't return a value. Look to `Function` for a subroutine
    that returns any value
    """

    def __eq__(self, other):
        return isinstance(other, Procedure) and super().__eq__(other)

    def __str__(self):
        return "procedure {}{}({}) {{\n{}}}".format(
            self.binding,
            self.name,
            ", ".join("%" + str(x) for x in self.params),
            "\n".join(map(str, self.blocks.values())),
        )

    def compare_structure(self, other):
        return isinstance(other, Procedure) and super().compare_structure(other)


class ForwardDecl:
    """Base class for all forward declarations (for function and procedures)"""

    def __init__(self, name, params):
        assert all(isinstance(x, Parameter) for x in params)
        self.name = name
        self.params = params

    def __eq__(self, other):
        return (
            isinstance(other, ForwardDecl)
            and self.name == other.name
            and self.params == other.params
        )

    def __hash__(self):
        return hash((self.name, *self.params))


class FunctionForwardDecl(ForwardDecl):
    """A forward decleration for a function"""

    def __init__(self, name, params, ret_type):
        super().__init__(name, params)
        assert isinstance(ret_type, Type)
        self.ret_type = ret_type

    def __eq__(self, other):
        return (
            isinstance(other, FunctionForwardDecl)
            and self.ret_type == other.ret_type
            and super().__eq__(other)
        )

    def __hash__(self):
        return hash((super().__hash__(), self.ret_type))

    def __str__(self):
        return "function {} @{}({})".format(
            self.ret_type,
            self.name,
            ", ".join("%" + str(x) for x in self.params),
        )


class ProcedureForwardDecl(ForwardDecl):
    """A forward decleration for a procedure"""

    def __init__(self, name, params):
        super().__init__(name, params)

    def __eq__(self, other):
        return isinstance(other, ProcedureForwardDecl) and super().__eq__(other)

    def __hash__(self):
        return super().__hash__()

    def __str__(self):
        return "procedure @{}({})".format(
            self.name,
            ", ".join("%" + str(x) for x in self.params),
        )


class Instruction:
    """The base class for all instructions"""

    def __init__(self):
        self.block = None
        self.users = []
        self._used_vars = []

    def __eq__(self, other):
        return isinstance(other, Instruction)

    def add_used_vars(self, *variables):
        """
        Adds variables to an instruction's internal variables list. This is only meant
        to be used internally
        """
        for var in variables:
            assert isinstance(var, Instruction)
            if var not in self._used_vars:
                self._used_vars.append(var)
            var.add_user(self)

    def remove_used_vars(self, *variables):
        """
        Removes variables from an instruction's internal variables list. This is only meant
        to be used internally
        """
        for var in variables:
            assert isinstance(var, AssignmentInstruction)
            assert var in self.used_vars, "instr is not a registered variable"
            self._used_vars.remove(var)
            var.remove_user(self)

    def add_user(self, instr):
        """
        Adds a user to a instruction's internal users list. This is only meant to be used
        internally
        """
        assert isinstance(instr, Instruction)
        if instr not in self.users:
            self.users.append(instr)

    def remove_user(self, instr):
        """
        Removes a user from a instruction's internal users list. This is only meant to be
        used internally
        """
        assert isinstance(instr, Instruction)
        assert instr in self.users, "instr is not a registered user"
        self.users.remove(instr)

    def replace_by(self, value):
        """Replaces all uses of the current instruction with a different one"""
        for use in self.users[:]:
            use.replace_use(self, value)
        self.remove_used_vars(*self.used_vars)

    def replace_use(self, old, new):
        """Replaces all uses of `old` within the instruction with `new`"""
        assert isinstance(old, AssignmentInstruction)
        assert isinstance(new, AssignmentInstruction)
        assert any(
            x is old for x in self.used_vars
        ), "`old` was not found in the variables used"
        for var in self.used_vars:
            if var is old:
                self.remove_used_vars(var)
        self.add_used_vars(new)

    def get_operand_at(self, idx):
        """Returns the operand at a specific index"""
        raise NotImplementedError()

    def set_operand_at(self, idx, new):
        """Sets the operand at a specific index"""
        raise NotImplementedError()

    @property
    def operand_num(self):
        """Returns the number of operand the instruction has"""
        raise NotImplementedError()

    @property
    def operands(self):
        """Yields the list of operands the instruction uses"""
        for x in range(0, self.operand_num):
            yield self.get_operand_at(x)

    @property
    def opcode_name(self):
        raise NotImplementedError()

    @property
    def is_used(self):
        return bool(self.use_count)

    @property
    def use_count(self):
        return len(self.users)

    @property
    def used_vars(self):
        return self._used_vars

    @property
    def subroutine(self):
        assert (
            self.block
        ), "instruction has not been assigned a block yet, therfore it can not acess the block's parent subroutine"
        return self.block.subroutine


class AssignmentInstruction(Instruction):
    """Base class for all instructions that are a type of assignment"""

    def __init__(self, name, instr_type):
        super().__init__()
        assert isinstance(instr_type, Type)
        self.name = name
        self.instr_type = instr_type
        self.ssa_id = None

    def __hash__(self):
        return hash((self.name, self.instr_type, self.ssa_id))

    def __eq__(self, other):
        return (
            super().__eq__(other)
            and isinstance(other, AssignmentInstruction)
            and self.name == other.name
            and self.instr_type == other.instr_type
        )


class GlobalConst(AssignmentInstruction):
    """A global constant; Can not be set after it is defined!"""

    _const_id = 0

    def __init__(self, name, instr_type, value):
        assert isinstance(instr_type, Type)
        self.name = name
        self.instr_type = instr_type
        self.value = value
        self.users = []
        self.const_id = self._const_id
        self._const_id += 1

    def __hash__(self):
        return hash((self.name, self.instr_type, self.value, self.const_id))

    def __eq__(self, other):
        return (
            isinstance(other, GlobalConst)
            and self.name == other.name
            and self.instr_type == other.instr_type
            and self.value == other.value
            and self.const_id == other.const_id
        )

    def add_user(self, instr):
        """
        Adds a user to a variable's internal users list. This is only meant to be used
        internally
        """
        assert isinstance(instr, Instruction)
        if instr not in self.users:
            self.users.append(instr)

    def remove_user(self, instr):
        """
        Removes a user from a variable's internal users list. This is only meant to be
        used internally
        """
        assert isinstance(instr, Instruction)
        assert instr in self.users, "instr is not a registered user"
        self.users.remove(instr)

    @property
    def is_used(self):
        return bool(self.use_count)

    @property
    def use_count(self):
        return len(self.users)

    @property
    def opcode_name(self):
        return "gconst"


class Const(AssignmentInstruction):
    """A constant value (ie. 3, 3.14, etc)"""

    def __init__(self, name, instr_type, value):
        super().__init__(name, instr_type)
        self.name = name
        self.instr_type = instr_type
        self.value = value

    def __eq__(self, other):
        return (
            isinstance(other, Const)
            and super().__eq__(other)
            and self.value == other.value
        )

    def __hash__(self):
        return hash((super().__hash__(), self.value))

    def __str__(self):
        return "%{}.{}: {} = const {}".format(
            self.name, self.ssa_id, self.instr_type, self.value
        )

    def replace_use(self, old, new):
        raise Exception(
            "`Const` doesn't use any variables; invalid call to `replace_use`"
        )

    def get_operand_at(self, idx):
        assert idx == 0, "`idx` out of range"
        return self.value

    def set_operand_at(self, idx, new):
        assert idx == 0, "`idx` out of range"
        self.value = new

    @property
    def operand_num(self):
        return 1

    @property
    def opcode_name(self):
        return "const"


class BinOp(AssignmentInstruction):
    """"A binary operation of the form `op x y`"""

    def __init__(self, name, instr_type, op, x, y):
        super().__init__(name, instr_type)
        assert isinstance(op, Op)
        assert isinstance(x, AssignmentInstruction)
        assert isinstance(y, AssignmentInstruction)
        self.name = name
        self.instr_type = instr_type
        self.op = op
        self.x = x
        self.y = y
        self.add_used_vars(self.x, self.y)

    def __eq__(self, other):
        return (
            isinstance(other, BinOp)
            and super().__eq__(other)
            and self.op == other.op
            and self.x == other.x
            and self.y == other.y
        )

    def __hash__(self):
        return hash((super().__hash__(), self.op, self.x, self.y))

    def __str__(self):
        return "%{}.{}: {} = {} %{}.{} %{}.{}".format(
            self.name,
            self.ssa_id,
            self.instr_type,
            self.op,
            self.x.name,
            self.x.ssa_id,
            self.y.name,
            self.y.ssa_id,
        )

    def replace_use(self, old, new):
        super().replace_use(old, new)
        if self.x is old:
            self.x = new
        if self.y is old:
            self.y = new

    def get_operand_at(self, idx):
        assert 0 <= idx < 3, "`idx` out of range"
        return self.op if idx == 0 else self.x if idx == 1 else self.y

    def set_operand_at(self, idx, new):
        assert 0 <= idx < 3, "`idx` out of range"
        if idx == 0:
            self.op = new
        elif idx == 1:
            self.replace_use(self.x, new)
        else:
            self.replace_use(self.y, new)

    @property
    def operand_num(self):
        return 3

    @property
    def opcode_name(self):
        return str(self.op)


class Cast(AssignmentInstruction):
    """A conversion from one type to another"""

    def __init__(self, name, instr_type, value):
        super().__init__(name, instr_type)
        assert isinstance(value, AssignmentInstruction)
        self.name = name
        self.instr_type = instr_type
        self.value = value
        self.add_used_vars(self.value)

    def __eq__(self, other):
        return (
            isinstance(other, Cast)
            and super().__eq__(other)
            and self.value == other.value
        )

    def __hash__(self):
        return hash((super().__hash__(), self.value))

    def __str__(self):
        return "%{}.{}: {} = cast %{}.{}".format(
            self.name, self.ssa_id, self.instr_type, self.value.name, self.value.ssa_id
        )

    def replace_use(self, old, new):
        super().replace_use(old, new)
        self.value = new

    def get_operand_at(self, idx):
        assert idx == 0, "`idx` out of range"
        return self.value

    def set_operand_at(self, idx, new):
        assert idx == 0, "`idx` out of range"
        self.replace_use(self.value, new)

    @property
    def operand_num(self):
        return 1

    @property
    def opcode_name(self):
        return "cast"


class Id(AssignmentInstruction):
    """An copy operation of the form `x = y`"""

    def __init__(self, name, instr_type, value):
        super().__init__(name, instr_type)
        assert isinstance(value, AssignmentInstruction)
        self.name = name
        self.instr_type = instr_type
        self.value = value
        self.add_used_vars(self.value)

    def __eq__(self, other):
        return (
            isinstance(other, Id)
            and super().__eq__(other)
            and self.value == other.value
        )

    def __hash__(self):
        return hash((super().__hash__(), self.value))

    def __str__(self):
        return "%{}.{}: {} = id %{}.{}".format(
            self.name, self.ssa_id, self.instr_type, self.value.name, self.value.ssa_id
        )

    def replace_use(self, old, new):
        super().replace_use(old, new)
        self.value = new

    def get_operand_at(self, idx):
        assert idx == 0, "`idx` out of range"
        return self.value

    def set_operand_at(self, idx, new):
        assert idx == 0, "`idx` out of range"
        self.replace_use(self.value, new)

    @property
    def operand_num(self):
        return 1

    @property
    def opcode_name(self):
        return "id"


class Call(Instruction):
    """The base class for an instruction that invokes a subroutine"""

    def __init__(self, callee, params):
        super().__init__()
        assert all(isinstance(x, AssignmentInstruction) for x in params)
        self.callee = callee
        self._params = params
        self.add_used_vars(*self._params)

    def __eq__(self, other):
        return (
            isinstance(other, Call)
            and super().__eq__(other)
            and self.params == other.params
        )

    def __hash__(self):
        return hash((super().__hash__(), self.callee, tuple(self.params)))

    def add_param(self, param):
        """Adds a parameter to the call instruction's list of parameters"""
        assert isinstance(param, AssignmentInstruction)
        self._params.append(param)
        self.add_used_vars(param)

    def remove_param(self, param):
        """Removes a parameter from the call instruction's list of parameters"""
        assert isinstance(param, AssignmentInstruction)
        assert param in self._params, "parameter {} not found".format(param.name)
        self._params.remove(param)
        self.remove_used_vars(param)

    def replace_use(self, old, new):
        super().replace_use(old, new)
        for i, param in enumerate(self.params):
            if param is old:
                self._params[i] = new

    def get_operand_at(self, idx):
        assert 0 <= idx <= len(self.params), "`idx` out of range"
        return self.callee if idx == 0 else self.params[idx - 1]

    def set_operand_at(self, idx, new):
        assert 0 <= idx <= len(self.params), "`idx` out of range"
        if idx == 0:
            self.callee = new
        else:
            self.replace_use(self.params[idx - 1], new)

    @property
    def operand_num(self):
        return len(self.params) + 1

    @property
    def params(self):
        return self._params


class FunctionCall(AssignmentInstruction, Call):
    """An instruction that invokes a function (of type str)"""

    def __init__(self, name, instr_type, callee, params):
        AssignmentInstruction.__init__(self, name, instr_type)
        Call.__init__(self, callee, params)

    def __eq__(self, other):
        return (
            isinstance(other, FunctionCall)
            and self.callee == other.callee
            and super().__eq__(other)
        )

    def __str__(self):
        return "%{}.{}: {} = fcall {}({})".format(
            self.name,
            self.ssa_id,
            self.instr_type,
            self.callee,
            ", ".join("%{}.{}".format(x.name, x.ssa_id) for x in self.params),
        )

    @property
    def opcode_name(self):
        return "fcall"


class ProcedureCall(Call):
    """An instruction that invokes a procedure (of type str)"""

    def __eq__(self, other):
        return (
            isinstance(other, ProcedureCall)
            and self.callee == other.callee
            and super().__eq__(other)
        )

    def __str__(self):
        return "pcall {}({})".format(
            self.callee,
            ", ".join("%{}.{}".format(x.name, x.ssa_id) for x in self.params),
        )

    @property
    def opcode_name(self):
        return "pcall"


class Phi(AssignmentInstruction):
    """
    An imaginary instruction used to merge values based upon it's block's
    predecessors (to conform with SSA). If a block has more than one phi instruction,
    all of them execute simultaneously. All phi instructions get removed during
    register allocation
    """

    def __init__(self, name, instr_type):
        super().__init__(name, instr_type)
        self.name = name
        self.instr_type = instr_type
        self._inputs = []

    def __eq__(self, other):
        return (
            isinstance(other, Phi)
            and super().__eq__(other)
            and self.inputs == other.inputs
        )

    def __hash__(self):
        return hash((super().__hash__(), self.inputs))

    def __str__(self):
        return "%{}.{}: {} = phi({})".format(
            self.name,
            self.ssa_id,
            self.instr_type,
            ", ".join(
                "(.{}, %{}.{})".format(x.block.name, x.name, x.ssa_id)
                for x in self.inputs
            ),
        )

    def add_input(self, value):
        """Adds a parameter/input to the phi function"""
        assert isinstance(value, AssignmentInstruction)
        assert value.block, "`value` must be assigned a block"
        self._inputs.append(value)
        self.add_used_vars(value)

    def remove_input(self, value):
        """Removes a parameter/input from the phi function"""
        assert isinstance(value, AssignmentInstruction)
        assert value in self.inputs, "`value` not in the phi's inputs"
        self._inputs.remove(value)
        self.remove_used_vars(value)

    def replace_use(self, old, new):
        super().replace_use(old, new)
        self.inputs.insert(self.inputs.index(old), new)
        self._inputs.remove(old)

    def get_operand_at(self, idx):
        assert 0 <= idx < len(self.inputs) - 1, "`idx` out of range"
        return self.inputs[idx]

    def set_operand_at(self, idx, new):
        assert 0 <= idx < len(self.inputs) - 1, "`idx` out of range"
        self.replace_use(self.inputs[idx], new)

    @property
    def operand_num(self):
        return len(self.inputs)

    @property
    def inputs(self):
        return self._inputs

    @property
    def opcode_name(self):
        return "phi"


class Ubr(Instruction):
    """An unconditional branch to another block"""

    def __init__(self, to_block):
        super().__init__()
        assert isinstance(to_block, Block)
        self.to_block = to_block

    def __eq__(self, other):
        return (
            isinstance(other, Ubr)
            and super().__eq__(other)
            # We can't compare the blocks because we will go into an infinite loop if we do so
            and self.to_block.name == other.to_block.name
        )

    def __hash__(self):
        return hash((super().__hash__(), self.to_block.name))

    def __str__(self):
        return "ubr .{}".format(self.to_block.name)

    def replace_use(self, old, new):
        raise Exception(
            "`Ubr` doesn't use any variables; invalid call to `replace_use`"
        )

    def get_operand_at(self, idx):
        assert idx == 0, "`idx` out of range"
        return self.to_block

    def set_operand_at(self, idx, new_block):
        assert idx == 0, "`idx` out of range"
        self.to_block = new_block

    @property
    def operand_num(self):
        return 1

    @property
    def opcode_name(self):
        return "ubr"


class Cbr(Instruction):
    """A conditional branch to another block"""

    def __init__(self, cond, true_block, false_block):
        super().__init__()
        assert isinstance(cond, AssignmentInstruction)
        assert isinstance(true_block, Block)
        assert isinstance(false_block, Block)
        self.cond = cond
        self.true_block = true_block
        self.false_block = false_block
        self.add_used_vars(self.cond)

    def __eq__(self, other):
        return (
            isinstance(other, Cbr)
            and super().__eq__(other)
            and self.cond == other.cond
            # We can't compare the blocks because we will go into an infinite loop if we do so
            and self.true_block.name == other.true_block.name
            and self.false_block.name == other.false_block.name
        )

    def __hash__(self):
        return hash((super().__hash__(), self.cond, self.true_block, self.false_block))

    def __str__(self):
        return "cbr %{}.{} .{} .{}".format(
            self.cond.name,
            self.cond.ssa_id,
            self.true_block.name,
            self.false_block.name,
        )

    def replace_use(self, old, new):
        super().replace_use(old, new)
        self.cond = new

    def get_operand_at(self, idx):
        assert 0 <= idx < 3, "`idx` out of range"
        return (
            self.cond if idx == 0 else self.true_block if idx == 1 else self.false_block
        )

    def set_operand_at(self, idx, new):
        assert 0 <= idx < 3, "`idx` out of range"
        if idx == 0:
            self.replace_use(self.cond, new)
        elif idx == 1:
            self.true_block = new
        else:
            self.false_block = new

    @property
    def operand_num(self):
        return 3

    @property
    def opcode_name(self):
        return "cbr"


class Return(Instruction):
    """A return statement that returns control (and possibly a value) back to the caller"""

    def __init__(self, instr_type, value):
        super().__init__()
        assert isinstance(instr_type, Type)
        assert isinstance(value, AssignmentInstruction)
        self.instr_type = instr_type
        self.value = value
        self.add_used_vars(self.value)

    def __eq__(self, other):
        return (
            isinstance(other, Return)
            and super().__eq__(other)
            and self.instr_type == other.instr_type
            and self.value == other.value
        )

    def __hash__(self):
        return hash((super().__hash__(), self.value))

    def __str__(self):
        return "return %{}.{}".format(self.value.name, self.value.ssa_id)

    def replace_use(self, old, new):
        super().replace_use(old, new)
        self.value = new

    def get_operand_at(self, idx):
        assert idx == 0, "`idx` out of range"
        return self.value

    def set_operand_at(self, idx, new):
        assert idx == 0, "`idx` out of range"
        self.replace_use(self.value, new)

    @property
    def operand_num(self):
        return 1

    @property
    def opcode_name(self):
        return "return"
