"""Behavioral ownership checks for the production worker, independent of Docker."""

from decimal import Decimal
from uuid import uuid4

import pytest
from test_scheduling_phase8 import setup_test_org_and_mission

from syntra.domain.entities import AttemptState, MissionState, TaskState
from syntra.scheduling.exceptions import StaleLeaseError
from syntra.scheduling.models import TaskExecutionResult
from syntra.scheduling.scheduler import TaskScheduler

pytest_plugins = ["test_scheduling_phase8"]


async def prepare(uow_factory):
    async with uow_factory() as uow:
        org, mission, plan = await setup_test_org_and_mission(uow)
        await uow.tasks.create_task(
            task_id=uuid4(),
            task_plan_id=plan,
            mission_id=mission,
            org_id=org,
            identifier="T-10",
            title="Inspect fixture",
            description="Check input validation",
            assigned_role="backend_engineer",
        )
        await uow.commit()
    scheduler = TaskScheduler(uow_factory)
    (dispatch,) = await scheduler.schedule_ready_tasks(mission, org)
    return scheduler, dispatch


async def test_dispatch_can_start_only_once(uow_factory):
    scheduler, dispatch = await prepare(uow_factory)
    assert await scheduler.begin_dispatch(dispatch, "worker-10")
    assert not await scheduler.begin_dispatch(dispatch, "worker-10")
    assert not await scheduler.begin_dispatch(dispatch, "other-worker")
    await scheduler.assert_dispatch_active(dispatch, "worker-10")


@pytest.mark.parametrize(
    "field,value",
    [
        ("mission_id", uuid4()),
        ("org_id", uuid4()),
        ("assigned_role", "devops_engineer"),
        ("attempt_number", 3),
        ("fencing_token", 99),
        ("specification", "Injected command"),
        ("plan_version", 99),
    ],
)
async def test_forged_dispatch_never_starts(uow_factory, field, value):
    scheduler, dispatch = await prepare(uow_factory)
    assert not await scheduler.begin_dispatch(dispatch.model_copy(update={field: value}), "worker-10")
    assert await scheduler.begin_dispatch(dispatch, "worker-10")


async def test_cancellation_revokes_running_worker(uow_factory):
    scheduler, dispatch = await prepare(uow_factory)
    assert await scheduler.begin_dispatch(dispatch, "worker-10")
    async with uow_factory() as uow:
        mission = await uow.missions.get_by_id_for_org(dispatch.mission_id, dispatch.org_id)
        mission.state = MissionState.CANCELLED
        await uow.commit()
    with pytest.raises(StaleLeaseError):
        await scheduler.assert_dispatch_active(dispatch, "worker-10")
    with pytest.raises(StaleLeaseError):
        await scheduler.handle_task_completion(
            dispatch.mission_id,
            dispatch.org_id,
            TaskExecutionResult(
                task_id=dispatch.task_id,
                attempt_number=1,
                worker_id="worker-10",
                fencing_token=1,
                status=AttemptState.SUCCEEDED,
            ),
        )


async def test_completion_records_real_artifact_and_releases_full_reservation(uow_factory):
    scheduler, dispatch = await prepare(uow_factory)
    assert await scheduler.begin_dispatch(dispatch, "worker-10")
    result = TaskExecutionResult(
        task_id=dispatch.task_id,
        attempt_number=1,
        worker_id="worker-10",
        fencing_token=1,
        status=AttemptState.SUCCEEDED,
        unified_diff="--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-bad\n+good\n",
        actual_prompt_tokens=20,
        actual_completion_tokens=10,
        actual_cost_usd=Decimal("0.001"),
    )
    task = await scheduler.handle_task_completion(dispatch.mission_id, dispatch.org_id, result)
    assert task.state == TaskState.COMPLETED
    async with uow_factory() as uow:
        artifacts, _, _ = await uow.artifacts.list_for_mission(dispatch.mission_id, dispatch.org_id)
        assert artifacts and artifacts[0][1].storage_path.startswith("inline:")
        budget = await uow.budgets.get_for_mission(dispatch.mission_id)
        assert budget.reserved_tokens == 0
        assert budget.reserved_cost_usd == 0
        assert budget.consumed_tokens == 30
    with pytest.raises(StaleLeaseError):
        await scheduler.handle_task_completion(dispatch.mission_id, dispatch.org_id, result)
