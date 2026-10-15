"""Seed development organization, user, demo project, mission, approval, and generate signed test JWT tokens for manual verification."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import jwt
from sqlalchemy import select

from syntra.core.config import get_settings
from syntra.domain.entities import ApprovalActionType, ApprovalDecision, MembershipRole, compute_action_digest
from syntra.persistence.models import (
    BudgetModel,
    HumanApprovalModel,
    MembershipModel,
    MissionModel,
    OrganizationModel,
    ProjectModel,
    UserModel,
)
from syntra.storage.database import get_db_manager

DEV_ORG_ID = UUID("00000000-0000-0000-0000-000000000002")
DEV_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
DEV_ADMIN_ID = UUID("00000000-0000-0000-0000-000000000003")
DEMO_PROJECT_ID = UUID("00000000-0000-0000-0000-000000000010")
DEMO_MISSION_ID = UUID("00000000-0000-0000-0000-000000000020")
DEMO_APPROVAL_ID = UUID("00000000-0000-0000-0000-000000000030")
EXPIRES_AT = datetime(2026, 10, 25, 0, 0, 0, tzinfo=UTC)


async def seed() -> None:
    settings = get_settings()
    db = get_db_manager()
    await db.init_tables()
    session_factory = db.get_session_factory()

    async with session_factory() as session:
        # 1. Organization
        stmt_org = select(OrganizationModel).where(OrganizationModel.id == DEV_ORG_ID)
        res_org = await session.execute(stmt_org)
        org = res_org.scalar_one_or_none()
        if not org:
            org = OrganizationModel(id=DEV_ORG_ID, name="SYNTRA Dev Org", slug="syntra-dev-org")
            session.add(org)
            print(f"Created Org: {org.name} ({org.id})")
        else:
            print(f"Existing Org found: {org.name} ({org.id})")

        # 2. Developer User
        stmt_user = select(UserModel).where(UserModel.id == DEV_USER_ID)
        res_user = await session.execute(stmt_user)
        user = res_user.scalar_one_or_none()
        if not user:
            user = UserModel(id=DEV_USER_ID, email="developer@syntra.local", full_name="Lead Developer")
            session.add(user)
            membership = MembershipModel(org_id=DEV_ORG_ID, user_id=DEV_USER_ID, role=MembershipRole.DEVELOPER)
            session.add(membership)
            print(f"Created Developer User: {user.email} ({user.id})")
        else:
            print(f"Existing Developer User found: {user.email} ({user.id})")

        # 3. Admin User
        stmt_admin = select(UserModel).where(UserModel.id == DEV_ADMIN_ID)
        res_admin = await session.execute(stmt_admin)
        admin = res_admin.scalar_one_or_none()
        if not admin:
            admin = UserModel(id=DEV_ADMIN_ID, email="admin@syntra.local", full_name="System Admin")
            session.add(admin)
            admin_membership = MembershipModel(org_id=DEV_ORG_ID, user_id=DEV_ADMIN_ID, role=MembershipRole.ADMIN)
            session.add(admin_membership)
            print(f"Created Admin User: {admin.email} ({admin.id})")
        else:
            print(f"Existing Admin User found: {admin.email} ({admin.id})")

        # 4. Demo Project
        stmt_proj = select(ProjectModel).where(ProjectModel.id == DEMO_PROJECT_ID)
        res_proj = await session.execute(stmt_proj)
        proj = res_proj.scalar_one_or_none()
        if not proj:
            proj = ProjectModel(
                id=DEMO_PROJECT_ID,
                org_id=DEV_ORG_ID,
                name="SYNTRA Demo Project",
                slug="syntra-demo-project",
                description="Seeded project for manual verification",
            )
            session.add(proj)
            print(f"Created Demo Project: {proj.name} ({proj.id})")
        else:
            print(f"Existing Demo Project found: {proj.name} ({proj.id})")

        # 5. Demo Mission
        stmt_mission = select(MissionModel).where(MissionModel.id == DEMO_MISSION_ID)
        res_mission = await session.execute(stmt_mission)
        mission = res_mission.scalar_one_or_none()
        if not mission:
            mission = MissionModel(
                id=DEMO_MISSION_ID,
                org_id=DEV_ORG_ID,
                project_id=DEMO_PROJECT_ID,
                objective="Verify human approval and budget governance",
                state="DRAFT",
                version=1,
            )
            session.add(mission)
            print(f"Created Demo Mission: {mission.objective} ({mission.id})")
        else:
            print(f"Existing Demo Mission found: {mission.id}")

        # 6. Demo Budget
        stmt_budget = select(BudgetModel).where(BudgetModel.mission_id == DEMO_MISSION_ID)
        res_budget = await session.execute(stmt_budget)
        budget = res_budget.scalar_one_or_none()
        if not budget:
            budget = BudgetModel(
                org_id=DEV_ORG_ID,
                mission_id=DEMO_MISSION_ID,
                max_tokens=100000,
                max_cost_usd=Decimal("10.00"),
                consumed_tokens=0,
                consumed_cost_usd=Decimal("0.00"),
            )
            session.add(budget)
            print(f"Created Demo Budget for mission {DEMO_MISSION_ID}")
        else:
            print(f"Existing Demo Budget found for mission {DEMO_MISSION_ID}")

        # 7. Demo Approval Request
        action_digest = compute_action_digest(
            secret=settings.approval_secret_key,
            mission_id=DEMO_MISSION_ID,
            action_type=ApprovalActionType.DEPLOYMENT.value,
            target_resource="production-cluster",
            mission_version=1,
            expires_at=EXPIRES_AT,
        )

        stmt_app = select(HumanApprovalModel).where(HumanApprovalModel.id == DEMO_APPROVAL_ID)
        res_app = await session.execute(stmt_app)
        app_entry = res_app.scalar_one_or_none()
        if not app_entry:
            app_entry = HumanApprovalModel(
                id=DEMO_APPROVAL_ID,
                org_id=DEV_ORG_ID,
                mission_id=DEMO_MISSION_ID,
                action_type=ApprovalActionType.DEPLOYMENT.value,
                target_resource="production-cluster",
                action_digest=action_digest,
                mission_version=1,
                decision=ApprovalDecision.PENDING,
                expires_at=EXPIRES_AT,
            )
            session.add(app_entry)
            print(f"Created Demo Pending Approval: {app_entry.id}")
        else:
            print(f"Existing Demo Approval found: {app_entry.id} (Status: {app_entry.decision.value})")

        await session.commit()

    # Generate JWT Tokens for manual curl testing
    secret = settings.jwt_secret_key
    now = datetime.now(UTC)
    exp = now + timedelta(days=7)

    dev_token = jwt.encode(
        {
            "sub": str(DEV_USER_ID),
            "email": "developer@syntra.local",
            "org_id": str(DEV_ORG_ID),
            "role": "developer",
            "iss": settings.oidc_issuer or "https://auth.syntra.io",
            "aud": settings.oidc_audience or "syntra-api",
            "exp": exp,
            "iat": now,
        },
        secret,
        algorithm="HS256",
    )

    admin_token = jwt.encode(
        {
            "sub": str(DEV_ADMIN_ID),
            "email": "admin@syntra.local",
            "org_id": str(DEV_ORG_ID),
            "role": "admin",
            "iss": settings.oidc_issuer or "https://auth.syntra.io",
            "aud": settings.oidc_audience or "syntra-api",
            "exp": exp,
            "iat": now,
        },
        secret,
        algorithm="HS256",
    )

    print("\n" + "=" * 60)
    print("🔑 Generated Manual Testing Tokens & Seed IDs:")
    print("=" * 60)
    print(f"ORG ID:          {DEV_ORG_ID}")
    print(f"DEV USER ID:     {DEV_USER_ID}")
    print(f"ADMIN USER ID:   {DEV_ADMIN_ID}")
    print(f"DEMO PROJECT ID: {DEMO_PROJECT_ID}")
    print(f"DEMO MISSION ID: {DEMO_MISSION_ID}")
    print(f"APPROVAL ID:     {DEMO_APPROVAL_ID}")
    print(f"ACTION DIGEST:   {action_digest}")
    print("-" * 60)
    print(f"\n[DEVELOPER TOKEN]\n{dev_token}\n")
    print(f"[ADMIN TOKEN]\n{admin_token}\n")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed())
