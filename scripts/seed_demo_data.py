#!/usr/bin/env python3
"""Seed CivilPDF-DX with fictional, clearly-marked demo data (idempotent).

Purpose: populate a fresh MVP/prototype environment (local SQLite or a staging
PostgreSQL) so every major screen, search result, KPI, workflow, notification
and export has coherent data to show. All names, e-mail addresses, project
codes and file contents are fictional (reserved .example domain); nothing here
is production or personal data.

Usage (repository root):
    DATABASE_URL=sqlite:///./.mvp-data/civilpdf-mvp.db \
    UPLOAD_DIR=./.mvp-data/uploads \
    PYTHONPATH=src/console/backend \
    python scripts/seed_demo_data.py

Safe to re-run: rows are keyed by deterministic ids and are upserted.
`--reset` first removes every previously seeded demo row and its PDF files.
Demo login (all roles share one password for reviewer convenience):
    password: CivilPDF-Demo-2026!
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "src",
        "console",
        "backend",
    ),
)

from database import Base, SessionLocal, engine  # noqa: E402
from config import settings  # noqa: E402
from models.user import User, UserRole, UserStatus  # noqa: E402
from models.organization import Organization, OrgType  # noqa: E402
from models.document import (  # noqa: E402
    ApprovalStep,
    ApprovalWorkflow,
    Document,
    DocumentStatus,
    DocumentType,
    DocumentVersion,
)
from models.notification import Notification  # noqa: E402
from models.dx_sync_metric import DxSyncMetric  # noqa: E402
from models.consent import ConsentRecord  # noqa: E402
from models.ai_setting import AiSetting  # noqa: E402
from models.m365_setting import M365Setting  # noqa: E402
from models.user import Project, user_projects  # noqa: E402
from auth.jwt import get_password_hash  # noqa: E402
from services.retention_service import seed_default_policies, apply_retention_policy  # noqa: E402
from services.audit_chain_service import create_chained_audit_log  # noqa: E402

DEMO_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "civilpdf-dx-demo-data")
DEMO_PASSWORD = "CivilPDF-Demo-2026!"
DEMO_DOMAIN = "demo.civilpdf.example"


def _did(key: str) -> str:
    """Deterministic UUID for a demo entity so re-runs upsert the same rows."""
    return str(uuid.uuid5(DEMO_NAMESPACE, key))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _pdf_bytes(title: str, document_type: str) -> bytes:
    """Build a minimal, valid single-page PDF whose text marks it as demo data."""
    lines = [
        "CivilPDF-DX DEMO DOCUMENT",
        f"Title: {title}",
        f"Type: {document_type}",
        "This is fictional demo data for the MVP prototype.",
    ]
    escaped = [
        line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        for line in lines
    ]
    stream = (
        b"BT /F1 12 Tf 72 730 Td 16 TL\n"
        + b"\n".join(f"({line}) Tj T*".encode("ascii", "replace") for line in escaped)
        + b"\nET"
    )

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return bytes(out)


def _upsert(db, model, key: str, **values):
    row = db.query(model).filter(model.id == _did(key)).first()
    if row is None:
        row = model(id=_did(key), **values)
        db.add(row)
    else:
        for field, value in values.items():
            setattr(row, field, value)
    db.flush()
    return row


def _write_demo_pdf(doc: Document) -> None:
    upload_root = Path(settings.upload_dir) / "demo"
    upload_root.mkdir(parents=True, exist_ok=True)
    filename = f"{doc.id}.pdf"
    target = upload_root / filename
    if not target.exists():
        target.write_bytes(_pdf_bytes(doc.title, str(doc.document_type.value)))
    doc.filename = filename
    doc.file_path = str(target)
    doc.file_size = target.stat().st_size
    doc.page_count = 1


def seed(db) -> int:
    """Insert/refresh demo data. Returns number of documents written."""
    now = _utcnow()
    hashed_password = get_password_hash(DEMO_PASSWORD)

    hq = _upsert(
        db,
        Organization,
        "org:hq",
        name="みらい土木建設株式会社（デモ）",
        code="DEMO-HQ",
        org_type=OrgType.HEADQUARTERS,
        parent_id=None,
        path="/",
        is_active=True,
    )
    east = _upsert(
        db,
        Organization,
        "org:east",
        name="東日本支店（デモ）",
        code="DEMO-BR-EAST",
        org_type=OrgType.BRANCH,
        parent_id=hq.id,
        path=f"{hq.id}/",
        is_active=True,
    )
    west = _upsert(
        db,
        Organization,
        "org:west",
        name="西日本支店（デモ）",
        code="DEMO-BR-WEST",
        org_type=OrgType.BRANCH,
        parent_id=hq.id,
        path=f"{hq.id}/",
        is_active=True,
    )
    tokyo = _upsert(
        db,
        Organization,
        "org:tokyo",
        name="東京現場事務所（デモ）",
        code="DEMO-SITE-TOKYO",
        org_type=OrgType.SITE_OFFICE,
        parent_id=east.id,
        path=f"{hq.id}/{east.id}/",
        is_active=True,
    )
    osaka = _upsert(
        db,
        Organization,
        "org:osaka",
        name="大阪現場事務所（デモ）",
        code="DEMO-SITE-OSAKA",
        org_type=OrgType.SITE_OFFICE,
        parent_id=west.id,
        path=f"{hq.id}/{west.id}/",
        is_active=True,
    )
    fukuoka = _upsert(
        db,
        Organization,
        "org:fukuoka",
        name="福岡現場事務所（デモ）",
        code="DEMO-SITE-FUKUOKA",
        org_type=OrgType.SITE_OFFICE,
        parent_id=west.id,
        path=f"{hq.id}/{west.id}/",
        is_active=True,
    )

    user_specs = [
        (
            "user:admin",
            "admin@demo.civilpdf.example",
            "demo-admin",
            "工藤 恵一（デモ）",
            UserRole.ADMIN,
            hq.id,
        ),
        (
            "user:manager-east",
            "mgr-east@demo.civilpdf.example",
            "demo-mgr-east",
            "中村 拓海（デモ）",
            UserRole.MANAGER,
            east.id,
        ),
        (
            "user:manager-west",
            "mgr-west@demo.civilpdf.example",
            "demo-mgr-west",
            "佐伯 美咲（デモ）",
            UserRole.MANAGER,
            west.id,
        ),
        (
            "user:eng-tokyo",
            "eng-tokyo@demo.civilpdf.example",
            "demo-eng-tokyo",
            "高橋 蓮（デモ）",
            UserRole.ENGINEER,
            tokyo.id,
        ),
        (
            "user:eng-osaka",
            "eng-osaka@demo.civilpdf.example",
            "demo-eng-osaka",
            "田中 悠斗（デモ）",
            UserRole.ENGINEER,
            osaka.id,
        ),
        (
            "user:eng-fukuoka",
            "eng-fukuoka@demo.civilpdf.example",
            "demo-eng-fukuoka",
            "山本 千夏（デモ）",
            UserRole.ENGINEER,
            fukuoka.id,
        ),
        (
            "user:eng-tokyo2",
            "eng-tokyo2@demo.civilpdf.example",
            "demo-eng-tokyo2",
            "伊藤 誠（デモ）",
            UserRole.ENGINEER,
            tokyo.id,
        ),
        (
            "user:viewer-hq",
            "viewer@demo.civilpdf.example",
            "demo-viewer",
            "森田 彩花（デモ）",
            UserRole.VIEWER,
            hq.id,
        ),
        (
            "user:auditor",
            "auditor@demo.civilpdf.example",
            "demo-auditor",
            "監査法人 西村（デモ）",
            UserRole.VIEWER,
            hq.id,
        ),
        (
            "user:inactive",
            "retired@demo.civilpdf.example",
            "demo-retired",
            "小林 正則（デモ）",
            UserRole.VIEWER,
            east.id,
        ),
    ]
    users = {}
    for key, email, username, full_name, role, org_id in user_specs:
        users[key] = _upsert(
            db,
            User,
            key,
            email=email,
            username=username,
            full_name=full_name,
            hashed_password=hashed_password,
            role=role,
            status=UserStatus.INACTIVE if key == "user:inactive" else UserStatus.ACTIVE,
            organization_id=org_id,
            last_login=now - timedelta(hours=2) if key == "user:admin" else None,
        )

    project_specs = [
        (
            "project:expressway",
            "DEMO-PROJ-001",
            "道東自動車道 改良工事（デモ）",
            tokyo.id,
            "架空の高速道路改良工事。図面・安全書類・電子納品の一連フローを確認できます。",
        ),
        (
            "project:bridge",
            "DEMO-PROJ-002",
            "都市部高架橋 耐震補強工事（デモ）",
            tokyo.id,
            "架空の橋梁耐震補強。承認ワークフローとAI分類のデモ。",
        ),
        (
            "project:river",
            "DEMO-PROJ-003",
            "河川護岸 改修工事（デモ）",
            osaka.id,
            "架空の河川工事。検査記録と保持ポリシーのデモ。",
        ),
        (
            "project:ground",
            "DEMO-PROJ-004",
            "造成地盤 改良工事（デモ）",
            fukuoka.id,
            "架空の地盤改良工事。バージョン管理とリビジョンのデモ。",
        ),
        (
            "project:tunnel",
            "DEMO-PROJ-005",
            "山岳トンネル 照明設備更新（デモ）",
            tokyo.id,
            "架空の設備更新工事（完了済み・非アクティブ）。",
        ),
    ]
    projects = {}
    for key, code, name, org_id, description in project_specs:
        projects[key] = _upsert(
            db,
            Project,
            key,
            name=name,
            code=code,
            description=description,
            organization_id=org_id,
            is_active=(key != "project:tunnel"),
        )

    # Project membership: engineers/managers join their site's projects.
    member_map = {
        "project:expressway": [
            "user:eng-tokyo",
            "user:eng-tokyo2",
            "user:manager-east",
        ],
        "project:bridge": ["user:eng-tokyo", "user:manager-east", "user:viewer-hq"],
        "project:river": ["user:eng-osaka", "user:manager-west"],
        "project:ground": ["user:eng-fukuoka", "user:manager-west"],
        "project:tunnel": ["user:eng-tokyo2"],
    }
    for project_key, member_keys in member_map.items():
        project = projects[project_key]
        for member_key in member_keys:
            user = users[member_key]
            if user not in project.members:
                project.members.append(user)
    db.flush()

    seed_default_policies(db)

    doc_specs = [
        # (key, project_key, owner_key, title, type, status, revision, tags, ocr_text)
        (
            "doc:e1",
            "project:expressway",
            "user:eng-tokyo",
            "平面図 橋梁補修 区間A（デモ）",
            DocumentType.DRAWING,
            DocumentStatus.APPROVED,
            "B",
            ["平面図", "橋梁補修", "A区間"],
            "平面図 橋梁補修 区間A 鉄筋コンクリート 床版 施工計画 基礎工事",
        ),
        (
            "doc:e2",
            "project:expressway",
            "user:eng-tokyo",
            "断面図 高架橋 耐震補強（デモ）",
            DocumentType.DRAWING,
            DocumentStatus.APPROVED,
            "A",
            ["断面図", "耐震", "高架橋"],
            "断面図 高架橋 耐震補強 橋脚 耐震性能 鉄筋 配筋図",
        ),
        (
            "doc:e3",
            "project:expressway",
            "user:eng-tokyo2",
            "施工計画書 一式（デモ）",
            DocumentType.REPORT,
            DocumentStatus.PENDING_REVIEW,
            "1",
            ["施工計画", "承認待ち"],
            "施工計画書 工程表 仮設計画 安全対策 交通規制 工期",
        ),
        (
            "doc:e4",
            "project:expressway",
            "user:eng-tokyo",
            "安全書類 KY活動記録（デモ）",
            DocumentType.SAFETY,
            DocumentStatus.APPROVED,
            "0",
            ["安全", "KY"],
            "安全書類 KY活動記録 リスクアセスメント 墜落防止 重機災害",
        ),
        (
            "doc:e5",
            "project:expressway",
            "user:eng-tokyo",
            "下請契約書 一式（デモ）",
            DocumentType.CONTRACT,
            DocumentStatus.APPROVED,
            "1",
            ["契約", "下請"],
            "下請契約書 請負金額 工期 契約条件 電子帳簿保存法",
        ),
        (
            "doc:e6",
            "project:expressway",
            "user:eng-tokyo",
            "写真台帳 2026年7月（デモ）",
            DocumentType.PHOTO,
            DocumentStatus.DRAFT,
            "0",
            ["写真", "出来形"],
            "写真台帳 出来形 掘削 鉄筋組立 コンクリート打設 養生",
        ),
        (
            "doc:e7",
            "project:expressway",
            "user:eng-tokyo",
            "是正指示書 No.3（デモ）",
            DocumentType.CORRECTION,
            DocumentStatus.DRAFT,
            "0",
            ["是正", "品質"],
            "是正指示書 指摘事項 修正内容 再検査 品質管理",
        ),
        (
            "doc:b1",
            "project:bridge",
            "user:eng-tokyo",
            "構造図 橋脚 耐震補強（デモ）",
            DocumentType.DRAWING,
            DocumentStatus.PENDING_REVIEW,
            "A",
            ["構造図", "橋脚", "耐震"],
            "構造図 橋脚 耐震補強 鋼板巻立て アンカー 設計図",
        ),
        (
            "doc:b2",
            "project:bridge",
            "user:eng-tokyo2",
            "耐震診断 報告書（デモ）",
            DocumentType.REPORT,
            DocumentStatus.APPROVED,
            "2",
            ["耐震診断", "報告書"],
            "耐震診断 報告書 地震応答解析 保有水平耐力 補強設計",
        ),
        (
            "doc:b3",
            "project:bridge",
            "user:eng-tokyo",
            "検査記録 配筋検査（デモ）",
            DocumentType.INSPECTION,
            DocumentStatus.APPROVED,
            "1",
            ["検査", "配筋"],
            "検査記録 配筋検査 鉄筋径 間隔 かぶり厚 合格判定",
        ),
        (
            "doc:b4",
            "project:bridge",
            "user:eng-tokyo",
            "安全書類 足場組立計画（デモ）",
            DocumentType.SAFETY,
            DocumentStatus.PENDING_REVIEW,
            "0",
            ["安全", "足場"],
            "安全書類 足場組立計画 墜落制止用器具 手すり 安全帯",
        ),
        (
            "doc:r1",
            "project:river",
            "user:eng-osaka",
            "平面図 護岸 改修（デモ）",
            DocumentType.DRAWING,
            DocumentStatus.APPROVED,
            "B",
            ["平面図", "護岸", "河川"],
            "平面図 護岸 改修 河川 水制 根固め ブロック",
        ),
        (
            "doc:r2",
            "project:river",
            "user:eng-osaka",
            "検査記録 コンクリート強度（デモ）",
            DocumentType.INSPECTION,
            DocumentStatus.APPROVED,
            "3",
            ["検査", "コンクリート"],
            "検査記録 コンクリート強度 圧縮試験 養生 供試体",
        ),
        (
            "doc:r3",
            "project:river",
            "user:eng-osaka",
            "報告書 出水期前点検（デモ）",
            DocumentType.REPORT,
            DocumentStatus.PENDING_REVIEW,
            "1",
            ["報告書", "出水期"],
            "報告書 出水期前点検 河川構造物 洗掘 点検結果",
        ),
        (
            "doc:r4",
            "project:river",
            "user:eng-osaka",
            "契約書 材料供給（デモ）",
            DocumentType.CONTRACT,
            DocumentStatus.DRAFT,
            "0",
            ["契約", "材料"],
            "契約書 材料供給 骨材 セメント 単価 納期",
        ),
        (
            "doc:g1",
            "project:ground",
            "user:eng-fukuoka",
            "断面図 地盤改良（デモ）",
            DocumentType.DRAWING,
            DocumentStatus.PENDING_REVIEW,
            "A",
            ["断面図", "地盤改良"],
            "断面図 地盤改良 深層混合処理工法 改良深度 設計強度",
        ),
        (
            "doc:g2",
            "project:ground",
            "user:eng-fukuoka",
            "施工報告書 第2回（デモ）",
            DocumentType.REPORT,
            DocumentStatus.APPROVED,
            "2",
            ["報告書", "地盤"],
            "施工報告書 地盤改良 施工機械 日報 出来高 品質管理",
        ),
        (
            "doc:g3",
            "project:ground",
            "user:eng-fukuoka",
            "写真台帳 2026年6月（デモ）",
            DocumentType.PHOTO,
            DocumentStatus.DRAFT,
            "0",
            ["写真", "地盤"],
            "写真台帳 地盤改良 攪拌翼 固化材 施工状況",
        ),
        (
            "doc:t1",
            "project:tunnel",
            "user:eng-tokyo2",
            "設備図 照明配置（デモ）",
            DocumentType.DRAWING,
            DocumentStatus.APPROVED,
            "B",
            ["設備図", "照明"],
            "設備図 照明配置 トンネル 灯具 配線 照度",
        ),
        (
            "doc:t2",
            "project:tunnel",
            "user:eng-tokyo2",
            "検査記録 照度測定（デモ）",
            DocumentType.INSPECTION,
            DocumentStatus.ARCHIVED,
            "1",
            ["検査", "照度"],
            "検査記録 照度測定 平均照度 均斉度 合格判定",
        ),
        (
            "doc:e8",
            "project:expressway",
            "user:eng-tokyo",
            "旧版 平面図（ごみ箱デモ）",
            DocumentType.DRAWING,
            DocumentStatus.DRAFT,
            "0",
            ["旧版", "ごみ箱"],
            "旧版 平面図 誤登録 論理削除 ごみ箱デモ",
        ),
    ]

    documents = {}
    for spec in doc_specs:
        (
            key,
            project_key,
            owner_key,
            title,
            doc_type,
            status,
            revision,
            tags,
            ocr_text,
        ) = spec
        doc = _upsert(
            db,
            Document,
            key,
            title=title,
            document_type=doc_type,
            status=status,
            project_id=projects[project_key].id,
            owner_id=users[owner_key].id,
            revision=revision,
            tags=tags,
            ocr_text=ocr_text,
            ocr_processed=True,
            filename=f"{key.rsplit(':', 1)[-1]}.pdf",
            file_size=0,
            mime_type="application/pdf",
            iso19650_originator="MIR",
            iso19650_functional_breakdown="00",
            iso19650_form="DR" if doc_type == DocumentType.DRAWING else "RP",
            iso19650_discipline="ST" if "構造" in title else "CV",
            iso19650_number=key.rsplit(":", 1)[-1].upper(),
            created_at=now - timedelta(days=int(_did(key)[:8], 16) % 45),
            updated_at=now - timedelta(days=int(_did(key)[:8], 16) % 7),
        )
        if key == "doc:e8":
            doc.deletion_requested_at = now - timedelta(hours=5)
        if doc_type in (DocumentType.DRAWING, DocumentType.INSPECTION):
            doc.is_pdfa = True
            doc.pdfa_version = "PDF/A-2b"
        _write_demo_pdf(doc)
        apply_retention_policy(db, doc)
        documents[key] = doc

        if status in (DocumentStatus.APPROVED, DocumentStatus.PENDING_REVIEW):
            version_id = _did(f"ver:{key}")
            version = (
                db.query(DocumentVersion)
                .filter(DocumentVersion.id == version_id)
                .first()
            )
            if version is None:
                db.add(
                    DocumentVersion(
                        id=version_id,
                        document_id=doc.id,
                        version_number=1,
                        filename=doc.filename,
                        file_path=doc.file_path,
                        file_size=doc.file_size,
                        change_note="デモ用 初版登録",
                        created_by=users[owner_key].id,
                        created_at=doc.created_at,
                    )
                )

    workflow_specs = [
        # (key, doc_key, [(approver_key, status, comment)])
        ("wf:pending", "doc:e3", [("user:manager-east", "pending", None)]),
        (
            "wf:inprogress",
            "doc:b1",
            [
                ("user:eng-tokyo2", "approved", "内容確認OK"),
                ("user:manager-east", "pending", None),
            ],
        ),
        (
            "wf:approved",
            "doc:b3",
            [
                ("user:eng-tokyo2", "approved", "問題なし"),
                ("user:manager-east", "approved", "承認します"),
            ],
        ),
        (
            "wf:rejected",
            "doc:r3",
            [("user:manager-west", "rejected", "点検項目の追記をお願いします")],
        ),
        (
            "wf:three",
            "doc:g1",
            [
                ("user:eng-fukuoka", "approved", "確認済"),
                ("user:manager-west", "pending", None),
                ("user:auditor", "pending", None),
            ],
        ),
    ]
    for wf_key, doc_key, steps_spec in workflow_specs:
        doc = documents[doc_key]
        workflow = (
            db.query(ApprovalWorkflow)
            .filter(ApprovalWorkflow.document_id == doc.id)
            .first()
        )
        if workflow is None:
            workflow = ApprovalWorkflow(id=_did(wf_key), document_id=doc.id)
            db.add(workflow)
        statuses = [step_status for _, step_status, _ in steps_spec]
        if (
            "pending" in statuses
            and "rejected" not in statuses
            and "approved" not in statuses
        ):
            workflow.status = "pending"
        elif "rejected" in statuses:
            workflow.status = "rejected"
        elif "pending" in statuses:
            workflow.status = "in_progress"
        else:
            workflow.status = "approved"
        if workflow.status in ("approved", "rejected"):
            workflow.completed_at = now - timedelta(days=2)
        db.flush()

        for order, (approver_key, step_status, comment) in enumerate(
            steps_spec, start=1
        ):
            step_id = _did(f"{wf_key}:step:{order}")
            step = db.query(ApprovalStep).filter(ApprovalStep.id == step_id).first()
            if step is None:
                step = ApprovalStep(
                    id=step_id,
                    workflow_id=workflow.id,
                    approver_id=users[approver_key].id,
                    order=order,
                )
                db.add(step)
            step.status = step_status
            step.comment = comment
            step.decided_at = (
                now - timedelta(days=1) if step_status != "pending" else None
            )
            if step_status == "pending" and comment is None:
                notification_id = _did(f"notif:{wf_key}:{order}")
                notification = (
                    db.query(Notification)
                    .filter(Notification.id == notification_id)
                    .first()
                )
                if notification is None:
                    db.add(
                        Notification(
                            id=notification_id,
                            user_id=users[approver_key].id,
                            notification_type="workflow.assigned",
                            title=f"承認依頼: {doc.title}",
                            body=f"文書「{doc.title}」の承認をお願いします（デモ通知）。",
                            resource_type="workflow",
                            resource_id=workflow.id,
                            is_read=False,
                            created_at=now - timedelta(hours=3),
                        )
                    )

    admin_notices = [
        (
            "notif:admin:welcome",
            "デモ環境へようこそ",
            "CivilPDF-DX MVP の架空ダミーデータが投入されています。すべてデモ用です。",
            "system.demo_welcome",
        ),
        (
            "notif:admin:upload",
            "文書がアップロードされました（デモ）",
            "「平面図 橋梁補修 区間A（デモ）」が登録されました。",
            "document.uploaded",
        ),
    ]
    for notification_key, title, body, notification_type in admin_notices:
        notification_id = _did(notification_key)
        notification = (
            db.query(Notification).filter(Notification.id == notification_id).first()
        )
        if notification is None:
            db.add(
                Notification(
                    id=notification_id,
                    user_id=users["user:admin"].id,
                    notification_type=notification_type,
                    title=title,
                    body=body,
                    resource_type="system",
                    resource_id=None,
                    is_read=False,
                    created_at=now - timedelta(minutes=20),
                )
            )

    dx_events = [
        ("user:eng-tokyo", "doc:e1", "success", 200, None, "editor sync"),
        ("user:eng-tokyo", "doc:e2", "success", 200, None, "editor sync"),
        ("user:eng-tokyo2", "doc:b1", "success", 200, None, "editor sync"),
        ("user:eng-tokyo2", "doc:b2", "error", 413, "too_large", "sidecar too large"),
        ("user:eng-osaka", "doc:r1", "success", 200, None, "editor sync"),
        ("user:eng-fukuoka", "doc:g2", "error", 401, "auth", "invalid token"),
    ]
    for index, (user_key, doc_key, event_type, code, error_kind, detail) in enumerate(
        dx_events
    ):
        metric_id = _did(f"metric:{index}")
        if db.query(DxSyncMetric).filter(DxSyncMetric.id == metric_id).first() is None:
            db.add(
                DxSyncMetric(
                    id=metric_id,
                    user_id=users[user_key].id,
                    document_id=documents[doc_key].id,
                    event_type=event_type,
                    status_code=code,
                    error_kind=error_kind,
                    detail=detail,
                    created_at=now - timedelta(days=index),
                )
            )

    consent_keys = [
        ("user:admin", "privacy_policy", True),
        ("user:eng-tokyo", "data_processing", True),
        ("user:eng-osaka", "analytics", False),
        ("user:viewer-hq", "marketing", False),
    ]
    for index, (user_key, consent_type, granted) in enumerate(consent_keys):
        consent_id = _did(f"consent:{index}")
        if (
            db.query(ConsentRecord).filter(ConsentRecord.id == consent_id).first()
            is None
        ):
            db.add(
                ConsentRecord(
                    id=consent_id,
                    user_id=users[user_key].id,
                    consent_type=consent_type,
                    version="1.0",
                    granted=granted,
                    ip_address="203.0.113.20",
                    user_agent="CivilPDF-DX Demo Client",
                    source="web_ui",
                    disclosed_purpose="デモ用: 個人情報の取扱いに関する説明",
                    disclosed_retention_period="デモ: 5年",
                    disclosed_third_parties="なし",
                    created_at=now - timedelta(days=30 - index),
                )
            )

    ai_setting = db.query(AiSetting).filter(AiSetting.id == 1).first()
    if ai_setting is None:
        ai_setting = AiSetting(id=1)
        db.add(ai_setting)
    ai_setting.enabled = False
    ai_setting.api_key_enc = ""
    ai_setting.model_name = "claude-haiku-4-5-20251001"
    ai_setting.updated_by = users["user:admin"].id

    m365_setting = db.query(M365Setting).filter(M365Setting.id == 1).first()
    if m365_setting is None:
        m365_setting = M365Setting(id=1)
        db.add(m365_setting)
    # MVP では未連携状態を明示（画面が空にならないように既定値を設定）。
    m365_setting.enabled = False
    m365_setting.tenant_id = ""
    m365_setting.client_id = ""
    m365_setting.client_secret_enc = ""
    m365_setting.auto_provision = True
    m365_setting.default_role = "viewer"
    m365_setting.updated_by = users["user:admin"].id

    db.flush()
    create_chained_audit_log(
        db,
        user_id=users["user:admin"].id,
        action="system.demo_seeded",
        resource_type="system",
        resource_id=None,
        detail="fictional demo dataset seeded (idempotent)",
        ip_address="127.0.0.1",
    )

    # Keep the FTS index coherent with the seeded rows.
    from api.search import _rebuild_fts_index

    indexed = _rebuild_fts_index(db)
    db.commit()
    return indexed


def purge(db) -> None:
    """Remove demo rows by deterministic id (dependency order) and demo PDFs."""
    demo_org_ids = {
        _did(k)
        for k in [
            "org:hq",
            "org:east",
            "org:west",
            "org:tokyo",
            "org:osaka",
            "org:fukuoka",
        ]
    }
    demo_user_ids = {
        u.id for u in db.query(User).filter(User.email.like(f"%@{DEMO_DOMAIN}")).all()
    }
    demo_project_ids = {
        p.id for p in db.query(Project).filter(Project.code.like("DEMO-PROJ-%")).all()
    }
    demo_doc_ids = {
        d.id
        for d in db.query(Document)
        .filter(Document.project_id.in_(demo_project_ids))
        .all()
    } | {_did("doc:e8")}
    demo_wf_ids = {
        w.id
        for w in db.query(ApprovalWorkflow)
        .filter(ApprovalWorkflow.document_id.in_(demo_doc_ids))
        .all()
    }

    for model, column, ids in (
        (ApprovalStep, ApprovalStep.workflow_id, demo_wf_ids),
        (DocumentVersion, DocumentVersion.document_id, demo_doc_ids),
        (Notification, Notification.user_id, demo_user_ids),
        (DxSyncMetric, DxSyncMetric.user_id, demo_user_ids),
        (ConsentRecord, ConsentRecord.user_id, demo_user_ids),
    ):
        for row in db.query(model).filter(column.in_(ids)).all():
            db.delete(row)
    db.execute(
        user_projects.delete().where(
            (user_projects.c.user_id.in_(demo_user_ids))
            | (user_projects.c.project_id.in_(demo_project_ids))
        )
    )
    for model, ids in (
        (ApprovalWorkflow, demo_wf_ids),
        (Document, demo_doc_ids),
        (Project, demo_project_ids),
        (User, demo_user_ids),
        (Organization, demo_org_ids),
    ):
        for row in db.query(model).filter(model.id.in_(ids)).all():
            db.delete(row)
    db.commit()
    demo_dir = Path(settings.upload_dir) / "demo"
    if demo_dir.exists():
        for file in demo_dir.glob("*.pdf"):
            file.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed CivilPDF-DX demo data")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="remove previously seeded demo data before re-seeding",
    )
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if args.reset:
            purge(db)
        indexed = seed(db)
        users = (
            db.query(User)
            .filter(User.email.like(f"%@{DEMO_DOMAIN}"))
            .order_by(User.username)
            .all()
        )
    finally:
        db.close()

    print("CivilPDF-DX デモデータ投入完了（すべて架空・デモ用）")
    print(f"DB: {settings.database_url}")
    print(f"Uploads: {settings.upload_dir}")
    print(f"FTS indexed documents: {indexed}")
    print(f"共通パスワード: {DEMO_PASSWORD}")
    print("ログインアカウント:")
    for user in users:
        print(f"  - {user.email} (role={user.role.value}, status={user.status.value})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
