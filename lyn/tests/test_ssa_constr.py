import os
import unittest
import compiler.ir as ir
import compiler.ssa_constr as ssa


class TestSSAConstr(unittest.TestCase):
    """
    Runs a series of tests upon the SSA construction algorithm testing all of its features. You
    can find the program being build in each test case in `data/ssa_constr/<proc-name-without-test>`
    """

    def setUp(self):
        self.module = ir.Module("nested_control_flow")
        self.data_dir = "tests/data/ssa_constr/"
        self.results = {
            name: open(self.data_dir + name, "r") for name in os.listdir(self.data_dir)
        }

    def tearDown(self):
        for f in self.results.values():
            f.close()

    def check_new_defs(self, builder, block, *args):
        for v in args:
            self.assertIs(
                builder.get_reaching_def(v.name, block),
                v,
                "expected {} to be a direct reference to `{}`".format(v.name, v),
            )

    def test_simple_bb(self):
        proc = ir.Procedure("test_simple_bb", [], ir.Binding.LOCAL)
        self.module.add_subroutine(proc)

        builder = ssa.SSA()
        bb0 = proc.add_block(ir.Block("bb0"))

        # Block 0
        builder.add_sealed_block(bb0)
        i_0 = bb0.add_instr(builder.new_variable(ir.Const("i", ir.Type.I32, "1"), bb0))
        j_0 = bb0.add_instr(builder.new_variable(ir.Const("j", ir.Type.I32, "1"), bb0))
        k_0 = bb0.add_instr(
            builder.new_variable(
                ir.BinOp(
                    "k",
                    ir.Type.I32,
                    ir.Op.ADD,
                    builder.get_reaching_def("i", bb0),
                    builder.get_reaching_def("j", bb0),
                ),
                bb0,
            )
        )

        self.check_new_defs(builder, bb0, i_0, j_0, k_0)
        self.assertEqual(str(proc), self.results["simple_bb"].read())

    def test_multiple_bbs(self):
        proc = ir.Procedure("test_multiple_bbs", [], ir.Binding.LOCAL)
        self.module.add_subroutine(proc)

        builder = ssa.SSA()
        bb0 = proc.add_block(ir.Block("bb0"))
        bb1 = proc.add_block(ir.Block("bb1"))

        # Block 0
        builder.add_sealed_block(bb0)
        i_0 = bb0.add_instr(builder.new_variable(ir.Const("i", ir.Type.I32, "1"), bb0))
        j_0 = bb0.add_instr(builder.new_variable(ir.Const("j", ir.Type.I32, "0"), bb0))
        bb0.add_instr(ir.Ubr(bb1))

        self.check_new_defs(builder, bb0, i_0, j_0)

        # Block 1
        bb1.add_pred(bb0)
        builder.add_sealed_block(bb1)
        k_0 = bb1.add_instr(
            builder.new_variable(
                ir.BinOp(
                    "k",
                    ir.Type.I32,
                    ir.Op.ADD,
                    builder.get_reaching_def("i", bb1),
                    builder.get_reaching_def("j", bb1),
                ),
                bb1,
            )
        )

        self.check_new_defs(builder, bb1, k_0)
        self.assertIs(builder.get_reaching_def("i", bb1), i_0)
        self.assertIs(builder.get_reaching_def("j", bb1), j_0)
        self.assertEqual(str(proc), self.results["multiple_bbs"].read())

    def test_if_else(self):
        proc = ir.Procedure("test_if_else", [], ir.Binding.LOCAL)
        self.module.add_subroutine(proc)

        builder = ssa.SSA()
        bb0 = proc.add_block(ir.Block("bb0"))
        bb1 = proc.add_block(ir.Block("bb1"))
        bb2 = proc.add_block(ir.Block("bb2"))
        bb3 = proc.add_block(ir.Block("bb3"))

        # Block 0
        builder.add_sealed_block(bb0)
        i_0 = bb0.add_instr(builder.new_variable(ir.Const("i", ir.Type.I32, "0"), bb0))
        j_0 = bb0.add_instr(builder.new_variable(ir.Const("j", ir.Type.I32, "1"), bb0))
        t0_0 = bb0.add_instr(
            builder.new_variable(
                ir.BinOp(
                    "t0",
                    ir.Type.I1,
                    ir.Op.LT,
                    builder.get_reaching_def("i", bb0),
                    builder.get_reaching_def("j", bb0),
                ),
                bb0,
            )
        )
        bb0.add_instr(ir.Cbr(builder.get_reaching_def("t0", bb0), bb1, bb2))
        self.check_new_defs(builder, bb0, i_0, j_0, t0_0)

        # Block 1
        bb1.add_pred(bb0)
        builder.add_sealed_block(bb1)
        k_0 = bb1.add_instr(
            builder.new_variable(
                ir.BinOp(
                    "k",
                    ir.Type.I32,
                    ir.Op.ADD,
                    builder.get_reaching_def("i", bb1),
                    builder.get_reaching_def("j", bb1),
                ),
                bb1,
            )
        )
        bb1.add_instr(ir.Ubr(bb3))
        self.check_new_defs(builder, bb1, k_0)
        self.assertIs(builder.get_reaching_def("i", bb1), i_0)
        self.assertIs(builder.get_reaching_def("j", bb1), j_0)

        # Block 2
        bb2.add_pred(bb0)
        builder.add_sealed_block(bb2)
        k_1 = bb2.add_instr(
            builder.new_variable(
                ir.BinOp(
                    "k",
                    ir.Type.I32,
                    ir.Op.SUB,
                    builder.get_reaching_def("i", bb2),
                    builder.get_reaching_def("j", bb2),
                ),
                bb2,
            )
        )
        bb2.add_instr(ir.Ubr(bb3))
        self.check_new_defs(builder, bb2, k_1)
        self.assertIs(builder.get_reaching_def("i", bb2), i_0)
        self.assertIs(builder.get_reaching_def("j", bb2), j_0)

        # Block 3
        bb3.add_pred(bb1)
        bb3.add_pred(bb2)
        builder.add_sealed_block(bb3)
        l_0 = bb3.add_instr(
            builder.new_variable(
                ir.Id("l", ir.Type.I32, builder.get_reaching_def("k", bb3)), bb3
            )
        )
        self.check_new_defs(builder, bb3, l_0)
        self.assertIsInstance(builder.get_reaching_def("k", bb3), ir.Phi)
        self.assertEqual(str(proc), self.results["if_else"].read())

    def test_pruned_ssa(self):
        proc = ir.Procedure("test_pruned_ssa", [], ir.Binding.LOCAL)
        self.module.add_subroutine(proc)

        builder = ssa.SSA()
        bb0 = proc.add_block(ir.Block("bb0"))
        bb1 = proc.add_block(ir.Block("bb1"))
        bb2 = proc.add_block(ir.Block("bb2"))
        bb3 = proc.add_block(ir.Block("bb3"))

        # Block 0
        builder.add_sealed_block(bb0)
        i_0 = bb0.add_instr(builder.new_variable(ir.Const("i", ir.Type.I32, "0"), bb0))
        j_0 = bb0.add_instr(builder.new_variable(ir.Const("j", ir.Type.I32, "1"), bb0))
        t0_0 = bb0.add_instr(
            builder.new_variable(
                ir.BinOp(
                    "t0",
                    ir.Type.I1,
                    ir.Op.LT,
                    builder.get_reaching_def("i", bb0),
                    builder.get_reaching_def("j", bb0),
                ),
                bb0,
            )
        )
        bb0.add_instr(ir.Cbr(builder.get_reaching_def("t0", bb0), bb1, bb2))
        self.check_new_defs(builder, bb0, i_0, j_0, t0_0)

        # Block 1
        bb1.add_pred(bb0)
        builder.add_sealed_block(bb1)
        x_0 = bb1.add_instr(
            builder.new_variable(ir.Const("x", ir.Type.I32, "100"), bb1)
        )
        y_0 = bb1.add_instr(
            builder.new_variable(
                ir.Id("y", ir.Type.I32, builder.get_reaching_def("x", bb1)), bb1
            )
        )
        z_0 = bb1.add_instr(
            builder.new_variable(
                ir.Id("z", ir.Type.I32, builder.get_reaching_def("y", bb1)), bb1
            )
        )
        bb1.add_instr(ir.Ubr(bb3))
        self.check_new_defs(builder, bb1, x_0, y_0, z_0)

        # Block 2
        bb2.add_pred(bb0)
        builder.add_sealed_block(bb2)
        x_1 = bb2.add_instr(
            builder.new_variable(ir.Const("x", ir.Type.I32, "101"), bb2)
        )
        y_1 = bb2.add_instr(
            builder.new_variable(
                ir.Id("y", ir.Type.I32, builder.get_reaching_def("x", bb2)), bb2
            )
        )
        z_1 = bb2.add_instr(
            builder.new_variable(
                ir.Id("z", ir.Type.I32, builder.get_reaching_def("y", bb2)), bb2
            )
        )
        bb2.add_instr(ir.Ubr(bb3))
        self.check_new_defs(builder, bb2, x_1, y_1, z_1)

        # Block 3
        bb3.add_pred(bb1)
        bb3.add_pred(bb2)
        builder.add_sealed_block(bb3)
        l_0 = bb3.add_instr(
            builder.new_variable(
                ir.Id("l", ir.Type.I32, builder.get_reaching_def("z", bb3)), bb3
            )
        )
        self.check_new_defs(builder, bb3, l_0)
        self.assertIsInstance(builder.get_reaching_def("z", bb3), ir.Phi)
        self.assertEqual(str(proc), self.results["pruned_ssa"].read())

    def test_nested_control_flow(self):
        proc = ir.Procedure("test_nested_control_flow", [], ir.Binding.LOCAL)
        self.module.add_subroutine(proc)

        builder = ssa.SSA()
        bb0 = proc.add_block(ir.Block("bb0"))
        bb1 = proc.add_block(ir.Block("bb1"))
        bb2 = proc.add_block(ir.Block("bb2"))
        bb3 = proc.add_block(ir.Block("bb3"))
        bb4 = proc.add_block(ir.Block("bb4"))
        bb5 = proc.add_block(ir.Block("bb5"))
        bb6 = proc.add_block(ir.Block("bb6"))

        # Block 0
        builder.add_sealed_block(bb0)
        i_0 = bb0.add_instr(builder.new_variable(ir.Const("i", ir.Type.I32, "1"), bb0))
        j_0 = bb0.add_instr(builder.new_variable(ir.Const("j", ir.Type.I32, "1"), bb0))
        k_0 = bb0.add_instr(builder.new_variable(ir.Const("k", ir.Type.I32, "0"), bb0))
        bb0.add_instr(ir.Ubr(bb1))
        self.check_new_defs(builder, bb0, i_0, j_0, k_0)

        # Block 1
        bb1.add_pred(bb0)
        t0_0 = bb1.add_instr(
            builder.new_variable(ir.Const("t0", ir.Type.I32, "100"), bb1)
        )
        t1_0 = bb1.add_instr(
            builder.new_variable(
                ir.BinOp(
                    "t1",
                    ir.Type.I1,
                    ir.Op.LT,
                    builder.get_reaching_def("k", bb1),
                    builder.get_reaching_def("t0", bb1),
                ),
                bb1,
            )
        )
        bb1.add_instr(ir.Cbr(builder.get_reaching_def("t1", bb1), bb2, bb3))
        self.check_new_defs(builder, bb1, t0_0, t1_0)
        self.assertIsInstance(builder.get_reaching_def("k", bb1), ir.Phi)

        # Block 2
        bb2.add_pred(bb1)
        builder.add_sealed_block(bb2)
        t2_0 = bb2.add_instr(
            builder.new_variable(ir.Const("t2", ir.Type.I32, "20"), bb2)
        )
        t3_0 = bb2.add_instr(
            builder.new_variable(
                ir.BinOp(
                    "t3",
                    ir.Type.I1,
                    ir.Op.LT,
                    builder.get_reaching_def("j", bb2),
                    builder.get_reaching_def("t2", bb2),
                ),
                bb2,
            )
        )
        bb2.add_instr(ir.Cbr(builder.get_reaching_def("t3", bb2), bb4, bb5))
        self.check_new_defs(builder, bb2, t2_0, t3_0)
        self.assertIsInstance(builder.get_reaching_def("j", bb2), ir.Phi)

        # Block 3
        bb3.add_pred(bb1)
        bb3.add_instr(ir.Return(ir.Type.I32, builder.get_reaching_def("j", bb3)))
        self.assertIsInstance(builder.get_reaching_def("j", bb3), ir.Phi)

        # Block 4
        bb4.add_pred(bb2)
        builder.add_sealed_block(bb4)
        t4_0 = bb4.add_instr(
            builder.new_variable(ir.Const("t4", ir.Type.I32, "1"), bb4)
        )
        j_3 = bb4.add_instr(
            builder.new_variable(
                ir.Id(
                    "j",
                    ir.Type.I32,
                    builder.get_reaching_def("i", bb4),
                ),
                bb4,
            )
        )
        self.assertIsInstance(builder.get_reaching_def("k", bb4), ir.Phi)
        k_2 = bb4.add_instr(
            builder.new_variable(
                ir.BinOp(
                    "k",
                    ir.Type.I32,
                    ir.Op.ADD,
                    builder.get_reaching_def("k", bb4),
                    builder.get_reaching_def("t4", bb4),
                ),
                bb4,
            )
        )
        bb4.add_instr(ir.Ubr(bb6))
        self.check_new_defs(builder, bb4, t4_0, j_3, k_2)
        # A phi function will temporarily be placed here, and will later be replace with `i_0`
        self.assertIsInstance(builder.get_reaching_def("i", bb4), ir.Phi)

        # Block 5
        bb5.add_pred(bb2)
        builder.add_sealed_block(bb5)
        t5_0 = bb5.add_instr(
            builder.new_variable(ir.Const("t5", ir.Type.I32, "2"), bb5)
        )
        j_4 = bb5.add_instr(
            builder.new_variable(
                ir.Id(
                    "j",
                    ir.Type.I32,
                    builder.get_reaching_def("k", bb5),
                ),
                bb5,
            ),
        )
        self.assertIsInstance(builder.get_reaching_def("k", bb5), ir.Phi)
        k_3 = bb5.add_instr(
            builder.new_variable(
                ir.BinOp(
                    "k",
                    ir.Type.I32,
                    ir.Op.ADD,
                    builder.get_reaching_def("k", bb5),
                    builder.get_reaching_def("t5", bb5),
                ),
                bb5,
            ),
        )
        bb5.add_instr(ir.Ubr(bb6))
        self.check_new_defs(builder, bb5, t5_0, j_4, k_3)

        # Block 6
        bb1.add_pred(bb6)
        bb6.add_pred(bb4)
        bb6.add_pred(bb5)
        builder.add_sealed_block(bb1)
        builder.add_sealed_block(bb6)
        builder.add_sealed_block(bb3)
        l_0 = bb6.add_instr(
            builder.new_variable(
                ir.BinOp(
                    "l",
                    ir.Type.I32,
                    ir.Op.ADD,
                    builder.get_reaching_def("i", bb6),
                    builder.get_reaching_def("k", bb6),
                ),
                bb6,
            ),
        )
        bb6.add_instr(ir.Ubr(bb1))
        self.check_new_defs(builder, bb6, l_0)
        self.assertIsInstance(builder.get_reaching_def("k", bb6), ir.Phi)
        self.assertIs(builder.get_reaching_def("i", bb6), i_0)

        self.assertEqual(str(proc), self.results["nested_control_flow"].read())
