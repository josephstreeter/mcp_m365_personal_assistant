.PHONY: test test-smoke test-mail test-calendar test-files-phase3 test-teams-phase4 test-todo-phase5 test-onenote-phase6 test-phase7-phase8 test-todo-files test-collab-context

test:
	uv run --with pytest pytest -q tests/test_smoke.py tests/test_mail_phase1.py tests/test_calendar_phase2.py tests/test_files_phase3.py tests/test_teams_phase4.py tests/test_todo_phase5.py tests/test_onenote_phase6.py tests/test_phase7_phase8.py tests/test_validation_todo_files.py tests/test_validation_collab_context.py

test-smoke:
	uv run --with pytest pytest -q tests/test_smoke.py

test-mail:
	uv run --with pytest pytest -q tests/test_mail_phase1.py

test-calendar:
	uv run --with pytest pytest -q tests/test_calendar_phase2.py

test-files-phase3:
	uv run --with pytest pytest -q tests/test_files_phase3.py

test-teams-phase4:
	uv run --with pytest pytest -q tests/test_teams_phase4.py

test-todo-phase5:
	uv run --with pytest pytest -q tests/test_todo_phase5.py

test-onenote-phase6:
	uv run --with pytest pytest -q tests/test_onenote_phase6.py

test-phase7-phase8:
	uv run --with pytest pytest -q tests/test_phase7_phase8.py

test-todo-files:
	uv run --with pytest pytest -q tests/test_validation_todo_files.py

test-collab-context:
	uv run --with pytest pytest -q tests/test_validation_collab_context.py
