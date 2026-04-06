"""Unit tests for DelegationGraph graph-safe authority rules."""

import pytest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from caracal.core.delegation_graph import DelegationGraph
from caracal.db.models import DelegationEdgeModel, ExecutionMandate, Principal


@pytest.mark.unit
class TestDelegationGraphLineageParity:
    """Test graph-safe delegation semantics after single-lineage removal."""

    def setup_method(self):
        self.mock_db_session = Mock()
        self.graph = DelegationGraph(self.mock_db_session)

    def test_add_edge_allows_target_without_denormalized_lineage(self):
        source_mandate_id = uuid4()
        target_mandate_id = uuid4()

        source_mandate = Mock(
            mandate_id=source_mandate_id,
            subject_id=uuid4(),
            revoked=False,
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
            resource_scope=["provider:*"],
            action_scope=["infer"],
            network_distance=2,
        )
        target_mandate = Mock(
            mandate_id=target_mandate_id,
            subject_id=uuid4(),
            revoked=False,
            source_mandate_id=None,
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
            resource_scope=["provider:openai:models"],
            action_scope=["infer"],
            network_distance=1,
        )

        source_principal = Mock(principal_kind="human")
        target_principal = Mock(principal_kind="worker")

        mandate_query_count = {"count": 0}
        principal_query_count = {"count": 0}

        def query_side_effect(model):
            query = Mock()
            if model == ExecutionMandate:
                mandate_query_count["count"] += 1
                if mandate_query_count["count"] == 1:
                    query.filter.return_value.first.return_value = source_mandate
                else:
                    query.filter.return_value.first.return_value = target_mandate
            elif model == Principal:
                principal_query_count["count"] += 1
                if principal_query_count["count"] == 1:
                    query.filter.return_value.first.return_value = source_principal
                else:
                    query.filter.return_value.first.return_value = target_principal
            elif model == DelegationEdgeModel:
                query.filter.return_value.first.return_value = None
            return query

        self.mock_db_session.query.side_effect = query_side_effect
        self.graph.get_authority_sources = Mock(return_value=[])

        edge = self.graph.add_edge(
            source_mandate_id=source_mandate_id,
            target_mandate_id=target_mandate_id,
            context_tags=["test"],
        )

        assert target_mandate.source_mandate_id is None
        assert edge.source_mandate_id == source_mandate_id
        assert edge.target_mandate_id == target_mandate_id
        self.mock_db_session.add.assert_called_once()

    def test_add_edge_ignores_stale_denormalized_target_lineage(self):
        source_mandate_id = uuid4()
        target_mandate_id = uuid4()

        source_mandate = Mock(
            mandate_id=source_mandate_id,
            subject_id=uuid4(),
            revoked=False,
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
            resource_scope=["provider:*"],
            action_scope=["infer"],
            network_distance=2,
        )
        target_mandate = Mock(
            mandate_id=target_mandate_id,
            subject_id=uuid4(),
            revoked=False,
            source_mandate_id=uuid4(),
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
            resource_scope=["provider:openai:models"],
            action_scope=["infer"],
            network_distance=1,
        )

        source_principal = Mock(principal_kind="human")
        target_principal = Mock(principal_kind="worker")

        mandate_query_count = {"count": 0}
        principal_query_count = {"count": 0}

        def query_side_effect(model):
            query = Mock()
            if model == ExecutionMandate:
                mandate_query_count["count"] += 1
                if mandate_query_count["count"] == 1:
                    query.filter.return_value.first.return_value = source_mandate
                else:
                    query.filter.return_value.first.return_value = target_mandate
            elif model == Principal:
                principal_query_count["count"] += 1
                if principal_query_count["count"] == 1:
                    query.filter.return_value.first.return_value = source_principal
                else:
                    query.filter.return_value.first.return_value = target_principal
            elif model == DelegationEdgeModel:
                query.filter.return_value.first.return_value = None
            return query

        self.mock_db_session.query.side_effect = query_side_effect
        self.graph.get_authority_sources = Mock(return_value=[])

        edge = self.graph.add_edge(
            source_mandate_id=source_mandate_id,
            target_mandate_id=target_mandate_id,
        )

        assert edge.source_mandate_id == source_mandate_id
        assert edge.target_mandate_id == target_mandate_id

    def test_add_edge_rejects_expired_source_mandate(self):
        source_mandate_id = uuid4()
        target_mandate_id = uuid4()

        source_mandate = Mock(
            mandate_id=source_mandate_id,
            subject_id=uuid4(),
            revoked=False,
            valid_from=datetime.utcnow() - timedelta(hours=2),
            valid_until=datetime.utcnow() - timedelta(minutes=1),
            network_distance=2,
        )
        target_mandate = Mock(
            mandate_id=target_mandate_id,
            subject_id=uuid4(),
            revoked=False,
            source_mandate_id=source_mandate_id,
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
            network_distance=1,
        )

        mandate_query_count = {"count": 0}

        def query_side_effect(model):
            query = Mock()
            if model == ExecutionMandate:
                mandate_query_count["count"] += 1
                if mandate_query_count["count"] == 1:
                    query.filter.return_value.first.return_value = source_mandate
                else:
                    query.filter.return_value.first.return_value = target_mandate
            return query

        self.mock_db_session.query.side_effect = query_side_effect

        with pytest.raises(ValueError, match="is not active"):
            self.graph.add_edge(
                source_mandate_id=source_mandate_id,
                target_mandate_id=target_mandate_id,
            )

    def test_add_edge_rejects_network_distance_mismatch(self):
        source_mandate_id = uuid4()
        target_mandate_id = uuid4()

        source_mandate = Mock(
            mandate_id=source_mandate_id,
            subject_id=uuid4(),
            revoked=False,
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
            network_distance=2,
        )
        target_mandate = Mock(
            mandate_id=target_mandate_id,
            subject_id=uuid4(),
            revoked=False,
            source_mandate_id=source_mandate_id,
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
            network_distance=2,
        )

        mandate_query_count = {"count": 0}

        def query_side_effect(model):
            query = Mock()
            if model == ExecutionMandate:
                mandate_query_count["count"] += 1
                if mandate_query_count["count"] == 1:
                    query.filter.return_value.first.return_value = source_mandate
                else:
                    query.filter.return_value.first.return_value = target_mandate
            return query

        self.mock_db_session.query.side_effect = query_side_effect

        with pytest.raises(ValueError, match="network_distance mismatch"):
            self.graph.add_edge(
                source_mandate_id=source_mandate_id,
                target_mandate_id=target_mandate_id,
            )

    def test_validate_authority_path_fails_closed_for_inactive_target(self):
        source_mandate_id = uuid4()
        target_mandate_id = uuid4()

        source_mandate = Mock(
            mandate_id=source_mandate_id,
            subject_id=uuid4(),
            revoked=False,
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
            network_distance=2,
        )
        inactive_target_mandate = Mock(
            mandate_id=target_mandate_id,
            subject_id=uuid4(),
            revoked=False,
            valid_from=datetime.utcnow() - timedelta(hours=2),
            valid_until=datetime.utcnow() - timedelta(minutes=1),
            network_distance=1,
        )

        self.graph._get_mandate = Mock(
            side_effect=lambda mandate_id: (
                source_mandate
                if mandate_id == source_mandate_id
                else inactive_target_mandate
                if mandate_id == target_mandate_id
                else None
            )
        )
        self.graph.get_delegated_targets = Mock(return_value=[])

        assert self.graph.validate_authority_path(source_mandate_id, target_mandate_id) is False

    def test_add_edge_rejects_cycle_when_reverse_path_exists(self):
        source_mandate_id = uuid4()
        target_mandate_id = uuid4()

        source_mandate = Mock(
            mandate_id=source_mandate_id,
            subject_id=uuid4(),
            revoked=False,
            source_mandate_id=None,
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
            resource_scope=["provider:*"],
            action_scope=["infer"],
            network_distance=2,
        )
        target_mandate = Mock(
            mandate_id=target_mandate_id,
            subject_id=uuid4(),
            revoked=False,
            source_mandate_id=source_mandate_id,
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
            resource_scope=["provider:openai:models"],
            action_scope=["infer"],
            network_distance=1,
        )

        self.graph._get_mandate = Mock(
            side_effect=lambda mandate_id: (
                source_mandate
                if mandate_id == source_mandate_id
                else target_mandate
                if mandate_id == target_mandate_id
                else None
            )
        )
        self.graph._is_mandate_active = Mock(return_value=True)
        self.graph.validate_authority_path = Mock(return_value=True)

        with pytest.raises(ValueError, match="cycle detected"):
            self.graph.add_edge(
                source_mandate_id=source_mandate_id,
                target_mandate_id=target_mandate_id,
            )

        self.graph.validate_authority_path.assert_called_once_with(
            target_mandate_id,
            source_mandate_id,
        )

    def test_add_edge_allows_multiple_active_inbound_edges(self):
        source_mandate_id = uuid4()
        target_mandate_id = uuid4()

        source_mandate = Mock(
            mandate_id=source_mandate_id,
            subject_id=uuid4(),
            revoked=False,
            source_mandate_id=None,
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
            resource_scope=["provider:*"],
            action_scope=["infer"],
            network_distance=2,
        )
        target_mandate = Mock(
            mandate_id=target_mandate_id,
            subject_id=uuid4(),
            revoked=False,
            source_mandate_id=source_mandate_id,
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
            resource_scope=["provider:openai:models"],
            action_scope=["infer"],
            network_distance=1,
        )

        source_principal = Mock(principal_kind="human")
        target_principal = Mock(principal_kind="worker")
        existing_inbound = Mock(source_mandate_id=uuid4(), revoked=False)
        existing_source_mandate = Mock(
            mandate_id=existing_inbound.source_mandate_id,
            revoked=False,
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
            resource_scope=["provider:*"],
            action_scope=["infer"],
            network_distance=3,
        )

        mandate_query_count = {"count": 0}
        principal_query_count = {"count": 0}
        edge_first_count = {"count": 0}

        def query_side_effect(model):
            query = Mock()
            if model == ExecutionMandate:
                mandate_query_count["count"] += 1
                if mandate_query_count["count"] == 1:
                    query.filter.return_value.first.return_value = source_mandate
                else:
                    query.filter.return_value.first.return_value = target_mandate
            elif model == Principal:
                principal_query_count["count"] += 1
                if principal_query_count["count"] == 1:
                    query.filter.return_value.first.return_value = source_principal
                else:
                    query.filter.return_value.first.return_value = target_principal
            elif model == DelegationEdgeModel:
                edge_first_count["count"] += 1
                # 1) reverse-path seed check, 2) duplicate source-target check, 3) active inbound check
                if edge_first_count["count"] in (1, 2):
                    query.filter.return_value.first.return_value = None
                else:
                    query.filter.return_value.first.return_value = existing_inbound
            return query

        self.mock_db_session.query.side_effect = query_side_effect
        self.graph.get_authority_sources = Mock(
            return_value=[SimpleNamespace(source_mandate_id=existing_inbound.source_mandate_id)]
        )
        self.graph._get_mandate = Mock(
            side_effect=lambda mandate_id: (
                source_mandate
                if mandate_id == source_mandate_id
                else target_mandate
                if mandate_id == target_mandate_id
                else existing_source_mandate
            )
        )

        edge = self.graph.add_edge(
            source_mandate_id=source_mandate_id,
            target_mandate_id=target_mandate_id,
        )

        assert edge.source_mandate_id == source_mandate_id
        assert edge.target_mandate_id == target_mandate_id

    def test_add_edge_rejects_scope_amplification_beyond_source_union(self):
        source_mandate_id = uuid4()
        other_source_mandate_id = uuid4()
        target_mandate_id = uuid4()

        source_mandate = Mock(
            mandate_id=source_mandate_id,
            subject_id=uuid4(),
            revoked=False,
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
            resource_scope=["provider:openai:*"],
            action_scope=["infer"],
            network_distance=2,
        )
        other_source_mandate = Mock(
            mandate_id=other_source_mandate_id,
            subject_id=uuid4(),
            revoked=False,
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
            resource_scope=["provider:anthropic:*"],
            action_scope=["infer"],
            network_distance=2,
        )
        target_mandate = Mock(
            mandate_id=target_mandate_id,
            subject_id=uuid4(),
            revoked=False,
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
            resource_scope=[
                "provider:openai:models",
                "provider:anthropic:models",
                "provider:google:models",
            ],
            action_scope=["infer"],
            network_distance=1,
        )

        source_principal = Mock(principal_kind="human")
        target_principal = Mock(principal_kind="worker")

        mandate_lookup = {
            source_mandate_id: source_mandate,
            other_source_mandate_id: other_source_mandate,
            target_mandate_id: target_mandate,
        }

        mandate_query_count = {"count": 0}
        principal_query_count = {"count": 0}
        edge_query_count = {"count": 0}

        def query_side_effect(model):
            query = Mock()
            if model == ExecutionMandate:
                mandate_query_count["count"] += 1
                if mandate_query_count["count"] == 1:
                    query.filter.return_value.first.return_value = source_mandate
                elif mandate_query_count["count"] == 2:
                    query.filter.return_value.first.return_value = target_mandate
                else:
                    predicate = query.filter.call_args
                    query.filter.return_value.first.side_effect = lambda: None
            elif model == Principal:
                principal_query_count["count"] += 1
                if principal_query_count["count"] == 1:
                    query.filter.return_value.first.return_value = source_principal
                else:
                    query.filter.return_value.first.return_value = target_principal
            elif model == DelegationEdgeModel:
                edge_query_count["count"] += 1
                query.filter.return_value.first.return_value = None
                query.filter.return_value.all.return_value = []
            return query

        self.mock_db_session.query.side_effect = query_side_effect
        self.graph.get_authority_sources = Mock(
            return_value=[SimpleNamespace(source_mandate_id=other_source_mandate_id)]
        )
        self.graph._get_mandate = Mock(side_effect=lambda mandate_id: mandate_lookup.get(mandate_id))

        with pytest.raises(ValueError, match="source union"):
            self.graph.add_edge(
                source_mandate_id=source_mandate_id,
                target_mandate_id=target_mandate_id,
            )

    def test_get_effective_scope_uses_union_of_active_sources(self):
        target_mandate_id = uuid4()
        source_one_id = uuid4()
        source_two_id = uuid4()

        target_mandate = SimpleNamespace(
            mandate_id=target_mandate_id,
            revoked=False,
            resource_scope=["provider:openai:models", "provider:anthropic:models"],
            action_scope=["infer", "embed"],
        )
        source_one = SimpleNamespace(
            mandate_id=source_one_id,
            revoked=False,
            resource_scope=["provider:openai:*"],
            action_scope=["infer"],
        )
        source_two = SimpleNamespace(
            mandate_id=source_two_id,
            revoked=False,
            resource_scope=["provider:anthropic:*"],
            action_scope=["embed"],
        )

        mandate_lookup = {
            target_mandate_id: target_mandate,
            source_one_id: source_one,
            source_two_id: source_two,
        }
        self.graph.get_authority_sources = Mock(
            return_value=[
                SimpleNamespace(source_mandate_id=source_one_id),
                SimpleNamespace(source_mandate_id=source_two_id),
            ]
        )

        def query_side_effect(model):
            query = Mock()
            if model == ExecutionMandate:
                query.filter.return_value.first.side_effect = lambda: mandate_lookup.popitem()[1]
            return query

        self.mock_db_session.query.side_effect = query_side_effect
        self.graph._get_mandate = Mock(side_effect=lambda mandate_id: {
            target_mandate_id: target_mandate,
            source_one_id: source_one,
            source_two_id: source_two,
        }.get(mandate_id))

        mandate_sequence = iter([target_mandate, source_one, source_two])

        def _execution_query(_model):
            query = Mock()
            query.filter.return_value.first.side_effect = lambda: next(mandate_sequence)
            return query

        self.mock_db_session.query.side_effect = _execution_query

        effective_scope = self.graph.get_effective_scope(target_mandate_id)

        assert effective_scope == {
            "resource_scope": ["provider:anthropic:models", "provider:openai:models"],
            "action_scope": ["embed", "infer"],
        }

    def test_validate_authority_path_supports_one_to_many_graphs(self):
        source_mandate_id = uuid4()
        target_one_id = uuid4()
        target_two_id = uuid4()

        source_mandate = SimpleNamespace(
            mandate_id=source_mandate_id,
            revoked=False,
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
        )
        target_one = SimpleNamespace(
            mandate_id=target_one_id,
            revoked=False,
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
        )
        target_two = SimpleNamespace(
            mandate_id=target_two_id,
            revoked=False,
            valid_from=datetime.utcnow() - timedelta(minutes=5),
            valid_until=datetime.utcnow() + timedelta(minutes=30),
        )

        self.graph._get_mandate = Mock(
            side_effect=lambda mandate_id: {
                source_mandate_id: source_mandate,
                target_one_id: target_one,
                target_two_id: target_two,
            }.get(mandate_id)
        )
        self.graph.get_delegated_targets = Mock(
            side_effect=lambda mandate_id, active_only=True: (
                [
                    SimpleNamespace(target_mandate_id=target_one_id),
                    SimpleNamespace(target_mandate_id=target_two_id),
                ]
                if mandate_id == source_mandate_id and active_only
                else []
            )
        )

        assert self.graph.validate_authority_path(source_mandate_id, target_one_id) is True
        assert self.graph.validate_authority_path(source_mandate_id, target_two_id) is True

    def test_validate_authority_path_supports_many_to_many_graphs(self):
        source_a_id = uuid4()
        source_b_id = uuid4()
        target_a_id = uuid4()
        target_b_id = uuid4()

        active_mandates = {
            source_a_id: SimpleNamespace(
                mandate_id=source_a_id,
                revoked=False,
                valid_from=datetime.utcnow() - timedelta(minutes=5),
                valid_until=datetime.utcnow() + timedelta(minutes=30),
            ),
            source_b_id: SimpleNamespace(
                mandate_id=source_b_id,
                revoked=False,
                valid_from=datetime.utcnow() - timedelta(minutes=5),
                valid_until=datetime.utcnow() + timedelta(minutes=30),
            ),
            target_a_id: SimpleNamespace(
                mandate_id=target_a_id,
                revoked=False,
                valid_from=datetime.utcnow() - timedelta(minutes=5),
                valid_until=datetime.utcnow() + timedelta(minutes=30),
            ),
            target_b_id: SimpleNamespace(
                mandate_id=target_b_id,
                revoked=False,
                valid_from=datetime.utcnow() - timedelta(minutes=5),
                valid_until=datetime.utcnow() + timedelta(minutes=30),
            ),
        }

        edges_by_source = {
            source_a_id: [
                SimpleNamespace(target_mandate_id=target_a_id),
                SimpleNamespace(target_mandate_id=target_b_id),
            ],
            source_b_id: [
                SimpleNamespace(target_mandate_id=target_a_id),
                SimpleNamespace(target_mandate_id=target_b_id),
            ],
        }

        self.graph._get_mandate = Mock(side_effect=lambda mandate_id: active_mandates.get(mandate_id))
        self.graph.get_delegated_targets = Mock(
            side_effect=lambda mandate_id, active_only=True: edges_by_source.get(mandate_id, [])
            if active_only
            else []
        )

        assert self.graph.validate_authority_path(source_a_id, target_b_id) is True
        assert self.graph.validate_authority_path(source_b_id, target_a_id) is True
