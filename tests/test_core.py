"""Testes automáticos da base (Fase 1). Não abrem janelas.

Executar:  python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from app.config import MODE_MONITOR, SettingsManager
from app.core.activity import ActivityLog
from app.core.dashboard_service import DashboardService
from app.core.paths import Paths
from app.core.timeutil import now_str
from app.database.database import Database
from app.database.migrations import MIGRATIONS, run_migrations
from app.database.models import LogCategory, TaskStatus
from app.scheduler.tasks import NewTask, TaskRepository


class TempDirTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.paths = Paths(Path(self._tmp.name))
        self.paths.ensure()

    def tearDown(self) -> None:
        if hasattr(self, "db"):
            self.db.close()
        self._tmp.cleanup()

    def make_db(self) -> Database:
        self.db = Database(self.paths.database_file)
        run_migrations(self.db, backup_dir=self.paths.backups)
        return self.db


class SettingsTests(TempDirTest):
    def test_creates_file_with_defaults(self):
        s = SettingsManager(self.paths.settings_file)
        s.load()
        self.assertTrue(self.paths.settings_file.exists())
        self.assertEqual(s.get("automation.mode"), MODE_MONITOR)
        self.assertEqual(s.get("business.payment_info"), "")

    def test_keeps_user_values_and_adds_new_keys(self):
        self.paths.settings_file.write_text(
            json.dumps({"business": {"company_name": "KRB"}}), encoding="utf-8"
        )
        s = SettingsManager(self.paths.settings_file)
        s.load()
        self.assertEqual(s.get("business.company_name"), "KRB")
        self.assertEqual(s.get("automation.auto_threshold"), 0.90)

    def test_corrupted_file_is_backed_up(self):
        self.paths.settings_file.write_text("{ isso não é json", encoding="utf-8")
        s = SettingsManager(self.paths.settings_file)
        s.load()
        self.assertEqual(s.get("automation.mode"), MODE_MONITOR)
        self.assertTrue(list(self.paths.config.glob("settings.json.corrupt-*")))

    def test_invalid_values_are_corrected(self):
        self.paths.settings_file.write_text(
            json.dumps({"automation": {"mode": "XYZ", "auto_threshold": 5, "approval_threshold": 0.95}}),
            encoding="utf-8",
        )
        s = SettingsManager(self.paths.settings_file)
        s.load()
        self.assertEqual(s.get("automation.mode"), MODE_MONITOR)
        self.assertEqual(s.get("automation.auto_threshold"), 1.0)
        self.assertLessEqual(s.get("automation.approval_threshold"), s.get("automation.auto_threshold"))

    def test_set_persists_and_notifies(self):
        s = SettingsManager(self.paths.settings_file)
        s.load()
        seen = []
        s.add_listener(lambda k, v: seen.append((k, v)))
        s.set("automation.paused", True)
        self.assertEqual(seen, [("automation.paused", True)])
        reloaded = SettingsManager(self.paths.settings_file)
        reloaded.load()
        self.assertTrue(reloaded.get("automation.paused"))


class DatabaseTests(TempDirTest):
    def test_migrations_create_tables(self):
        db = self.make_db()
        tables = {r["name"] for r in db.query_all("SELECT name FROM sqlite_master WHERE type='table'")}
        for name in (
            "contacts", "messages", "conversations", "orders", "order_items", "tasks",
            "automation_rules", "message_templates", "pending_responses", "settings", "logs",
        ):
            self.assertIn(name, tables)
        self.assertEqual(db.query_value("SELECT MAX(version) FROM schema_migrations"), MIGRATIONS[-1][0])

    def test_migrations_are_idempotent_and_keep_data(self):
        db = self.make_db()
        ts = now_str()
        db.execute("INSERT INTO contacts (name, phone, created_at, updated_at) VALUES ('A', '1', ?, ?)", (ts, ts))
        run_migrations(db, backup_dir=self.paths.backups)
        self.assertEqual(db.query_value("SELECT COUNT(*) FROM contacts"), 1)

    def test_pix_rule_starts_disabled(self):
        db = self.make_db()
        rule = db.query_one("SELECT enabled FROM automation_rules WHERE key = 'enviar_pix'")
        self.assertEqual(rule["enabled"], 0)

    def test_duplicate_external_id_is_rejected(self):
        db = self.make_db()
        ts = now_str()
        cid = db.execute("INSERT INTO contacts (name, phone, created_at, updated_at) VALUES ('A','1',?,?)", (ts, ts))
        sql = (
            "INSERT OR IGNORE INTO messages (contact_id, external_id, direction, body, timestamp, created_at) "
            "VALUES (?, 'wa-1', 'IN', 'oi', ?, ?)"
        )
        db.execute(sql, (cid, ts, ts))
        db.execute(sql, (cid, ts, ts))
        self.assertEqual(db.query_value("SELECT COUNT(*) FROM messages"), 1)

    def test_transaction_rolls_back(self):
        db = self.make_db()
        ts = now_str()
        with self.assertRaises(RuntimeError):
            with db.transaction() as conn:
                conn.execute("INSERT INTO contacts (name, phone, created_at, updated_at) VALUES ('A','1',?,?)", (ts, ts))
                raise RuntimeError("falha simulada")
        self.assertEqual(db.query_value("SELECT COUNT(*) FROM contacts"), 0)


class ServicesTests(TempDirTest):
    def test_tasks_and_dashboard(self):
        db = self.make_db()
        tasks = TaskRepository(db)
        later = tasks.create(NewTask("Depois", datetime.now() + timedelta(hours=2)))
        sooner = tasks.create(NewTask("Antes", datetime.now() + timedelta(hours=1)))
        no_time = tasks.create(NewTask("Sem horário"))
        self.assertEqual([t["id"] for t in tasks.upcoming()], [sooner, later, no_time])
        tasks.set_status(sooner, TaskStatus.CONCLUIDA)
        self.assertNotIn(sooner, [t["id"] for t in tasks.upcoming()])
        with self.assertRaises(ValueError):
            tasks.create(NewTask("   "))

        ts = now_str()
        cid = db.execute("INSERT INTO contacts (name, phone, created_at, updated_at) VALUES ('Ana','1',?,?)", (ts, ts))
        db.execute("INSERT INTO orders (contact_id, status, created_at, updated_at) VALUES (?, 'PRONTO', ?, ?)", (cid, ts, ts))
        db.execute("INSERT INTO orders (contact_id, status, created_at, updated_at) VALUES (?, 'ENTREGUE', ?, ?)", (cid, ts, ts))
        dash = DashboardService(db)
        stats = dash.stats()
        self.assertEqual(stats.ready, 1)
        self.assertEqual(stats.orders_today, 2)
        self.assertEqual(len(dash.open_orders()), 1)

    def test_activity_log(self):
        db = self.make_db()
        activity = ActivityLog(db)
        activity.record(LogCategory.SISTEMA, "teste")
        activity.error("problema")
        rows = activity.recent()
        self.assertEqual(rows[0]["category"], "ERRO")
        self.assertEqual(len(activity.recent(category="SISTEMA")), 1)


if __name__ == "__main__":
    os.environ.setdefault("KRB_HOME", tempfile.mkdtemp())
    unittest.main()
