# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# pyre-strict
from textwrap import dedent
from typing import Tuple

import libcst as cst
import libcst.matchers as m
import libcst.metadata as meta
from libcst.matchers import matches
from libcst.testing.utils import UnitTest


class MatchersMetadataTest(UnitTest):
    def _make_fixture(
        self, code: str
    ) -> Tuple[cst.BaseExpression, meta.MetadataWrapper]:
        module = cst.parse_module(dedent(code))
        wrapper = cst.MetadataWrapper(module)
        return (
            cst.ensure_type(
                cst.ensure_type(wrapper.module.body[0], cst.SimpleStatementLine).body[
                    0
                ],
                cst.Expr,
            ).value,
            wrapper,
        )

    def _make_coderange(
        self, start: Tuple[int, int], end: Tuple[int, int]
    ) -> cst.CodeRange:
        return cst.CodeRange(
            start=cst.CodePosition(line=start[0], column=start[1]),
            end=cst.CodePosition(line=end[0], column=end[1]),
        )

    def test_simple_matcher_true(self) -> None:
        # Match on a simple node based on the type and the position.
        node, wrapper = self._make_fixture("foo")
        self.assertTrue(
            matches(
                node,
                m.Name(
                    value="foo",
                    metadata=m.MatchMetadata(
                        meta.SyntacticPositionProvider,
                        self._make_coderange((1, 0), (1, 3)),
                    ),
                ),
                metadata_resolver=wrapper,
            )
        )
        # Match on any binary expression where the two children are in exact spots.
        node, wrapper = self._make_fixture("a + b")
        self.assertTrue(
            matches(
                node,
                m.BinaryOperation(
                    left=m.MatchMetadata(
                        meta.SyntacticPositionProvider,
                        self._make_coderange((1, 0), (1, 1)),
                    ),
                    right=m.MatchMetadata(
                        meta.SyntacticPositionProvider,
                        self._make_coderange((1, 4), (1, 5)),
                    ),
                ),
                metadata_resolver=wrapper,
            )
        )

    def test_simple_matcher_false(self) -> None:
        # Fail to match on a simple node based on the type and the position.
        node, wrapper = self._make_fixture("foo")
        self.assertFalse(
            matches(
                node,
                m.Name(
                    value="foo",
                    metadata=m.MatchMetadata(
                        meta.SyntacticPositionProvider,
                        self._make_coderange((2, 0), (2, 3)),
                    ),
                ),
                metadata_resolver=wrapper,
            )
        )
        # Fail to match on any binary expression where the two children are in exact spots.
        node, wrapper = self._make_fixture("foo + bar")
        self.assertFalse(
            matches(
                node,
                m.BinaryOperation(
                    left=m.MatchMetadata(
                        meta.SyntacticPositionProvider,
                        self._make_coderange((1, 0), (1, 1)),
                    ),
                    right=m.MatchMetadata(
                        meta.SyntacticPositionProvider,
                        self._make_coderange((1, 4), (1, 5)),
                    ),
                ),
                metadata_resolver=wrapper,
            )
        )

    def test_predicate_logic(self) -> None:
        # Verify that we can or things together.
        matcher = m.BinaryOperation(
            left=m.OneOf(
                m.MatchMetadata(
                    meta.SyntacticPositionProvider, self._make_coderange((1, 0), (1, 1))
                ),
                m.MatchMetadata(
                    meta.SyntacticPositionProvider, self._make_coderange((1, 0), (1, 2))
                ),
            )
        )
        node, wrapper = self._make_fixture("a + b")
        self.assertTrue(matches(node, matcher, metadata_resolver=wrapper))
        node, wrapper = self._make_fixture("12 + 3")
        self.assertTrue(matches(node, matcher, metadata_resolver=wrapper))
        node, wrapper = self._make_fixture("123 + 4")
        self.assertFalse(matches(node, matcher, metadata_resolver=wrapper))

        # Verify that we can and things together
        matcher = m.BinaryOperation(
            left=m.AllOf(
                m.MatchMetadata(
                    meta.SyntacticPositionProvider, self._make_coderange((1, 0), (1, 1))
                ),
                m.MatchMetadata(
                    meta.ExpressionContextProvider, meta.ExpressionContext.LOAD
                ),
            )
        )
        node, wrapper = self._make_fixture("a + b")
        self.assertTrue(matches(node, matcher, metadata_resolver=wrapper))
        node, wrapper = self._make_fixture("ab + cd")
        self.assertFalse(matches(node, matcher, metadata_resolver=wrapper))

        # Verify that we can not things
        matcher = m.BinaryOperation(
            left=m.DoesNotMatch(
                m.MatchMetadata(
                    meta.ExpressionContextProvider, meta.ExpressionContext.STORE
                )
            )
        )
        node, wrapper = self._make_fixture("a + b")
        self.assertTrue(matches(node, matcher, metadata_resolver=wrapper))

    def test_predicate_logic_operators(self) -> None:
        # Verify that we can or things together.
        matcher = m.BinaryOperation(
            left=(
                m.MatchMetadata(
                    meta.SyntacticPositionProvider, self._make_coderange((1, 0), (1, 1))
                )
                | m.MatchMetadata(
                    meta.SyntacticPositionProvider, self._make_coderange((1, 0), (1, 2))
                )
            )
        )
        node, wrapper = self._make_fixture("a + b")
        self.assertTrue(matches(node, matcher, metadata_resolver=wrapper))
        node, wrapper = self._make_fixture("12 + 3")
        self.assertTrue(matches(node, matcher, metadata_resolver=wrapper))
        node, wrapper = self._make_fixture("123 + 4")
        self.assertFalse(matches(node, matcher, metadata_resolver=wrapper))

        # Verify that we can and things together
        matcher = m.BinaryOperation(
            left=(
                m.MatchMetadata(
                    meta.SyntacticPositionProvider, self._make_coderange((1, 0), (1, 1))
                )
                & m.MatchMetadata(
                    meta.ExpressionContextProvider, meta.ExpressionContext.LOAD
                )
            )
        )
        node, wrapper = self._make_fixture("a + b")
        self.assertTrue(matches(node, matcher, metadata_resolver=wrapper))
        node, wrapper = self._make_fixture("ab + cd")
        self.assertFalse(matches(node, matcher, metadata_resolver=wrapper))

        # Verify that we can not things
        matcher = m.BinaryOperation(
            left=(
                ~m.MatchMetadata(
                    meta.ExpressionContextProvider, meta.ExpressionContext.STORE
                )
            )
        )
        node, wrapper = self._make_fixture("a + b")
        self.assertTrue(matches(node, matcher, metadata_resolver=wrapper))
