import copy

import compiler.ir as ir
from compiler.ssa_constr import SSA
from compiler.opt.lvn import LVN


def main():
    ssa = SSA()
    my_mod = ir.Module("my_mod")

    my_proc = ir.Procedure("my_proc", [], ir.Binding.GLOBAL)
    my_mod.add_subroutine(my_proc)
    block0 = my_proc.add_block(ir.Block("block0"))

    a = block0.add_instr(ssa.new_variable(ir.Const("a", ir.Type.I32, "100"), block0))
    b = block0.add_instr(ssa.new_variable(ir.Const("b", ir.Type.I32, "101"), block0))
    c = block0.add_instr(
        ssa.new_variable(
            ir.Id("c", ir.Type.I32, ssa.get_reaching_def("a", block0)), block0
        )
    )
    d = block0.add_instr(
        ssa.new_variable(
            ir.BinOp(
                "d",
                ir.Type.I32,
                ir.Op.ADD,
                ssa.get_reaching_def("a", block0),
                ssa.get_reaching_def("c", block0),
            ),
            block0,
        )
    )
    e = block0.add_instr(
        ssa.new_variable(
            ir.BinOp(
                "e",
                ir.Type.I32,
                ir.Op.ADD,
                ssa.get_reaching_def("a", block0),
                ssa.get_reaching_def("b", block0),
            ),
            block0,
        )
    )
    f = block0.add_instr(
        ssa.new_variable(
            ir.BinOp(
                "f",
                ir.Type.I32,
                ir.Op.ADD,
                ssa.get_reaching_def("d", block0),
                ssa.get_reaching_def("d", block0),
            ),
            block0,
        )
    )
    block0.add_instr(
        ir.ProcedureCall(
            "println",
            [ssa.get_reaching_def("e", block0), ssa.get_reaching_def("f", block0)],
        ),
    )
    old_mod = copy.deepcopy(my_mod)
    print(str(my_mod)[:-1])
    print("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-==-=-=-=-=-=-=-=-=")

    lvn = LVN()
    lvn.run_pass(block0)

    print(str(my_mod)[:-1])
    print("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-==-=-=-=-=-=-=-=-=")
    print(
        "the module HAS NOT changed" if old_mod == my_mod else "the module HAS changed"
    )


if __name__ == "__main__":
    main()
