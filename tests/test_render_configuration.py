from pathlib import Path


def test_render_blueprint_uses_free_snapshot_backed_single_instance():
    root = Path(__file__).resolve().parents[1]
    config = (root / "render.yaml").read_text(encoding="utf-8")
    assert "plan: free" in config
    assert "numInstances: 1" in config
    assert "autoDeployTrigger: checksPass" in config
    assert "healthCheckPath: /api/health" in config
    assert "WEB_STANDALONE" in config
    assert "DB_SYNC_WORKER_URL" in config
    assert "DB_SYNC_INSTALLATION_ID" in config
    assert "DB_SYNC_ENCRYPTION_SECRET" in config
    assert "disk:" not in config
    assert "AUDIT_DATA_DIR" not in config

    build_filter = config.split("buildFilter:", 1)[1].split("buildCommand:", 1)[0]
    assert "customer-data" not in build_filter
    assert "frontend/src/**" in build_filter
    assert "frontend/dist" not in build_filter

    workflow = (root / ".github" / "workflows" / "master.yml").read_text(encoding="utf-8")
    assert 'git commit -m "Publish freshly built web frontend bundle [skip render]"' in workflow



def test_frontend_bundle_publisher_skips_stale_builds_and_avoids_rebase_races():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "master.yml").read_text(encoding="utf-8")
    publish_step = workflow.split(
        "      - name: Publish built React frontend for the existing Render Python service",
        1,
    )[1].split("      - name:", 1)[0]

    assert "git fetch origin main" in publish_step
    assert "git merge-base --is-ancestor $env:GITHUB_SHA $latestMain" in publish_step
    assert "git diff --name-only $env:GITHUB_SHA $latestMain -- frontend assets" in publish_step
    assert '$staleInputs = @($changedSinceBuild | Where-Object { $_ -notlike "frontend/dist/*" })' in publish_step
    assert "git reset --hard $latestMain" in publish_step
    assert "Another concurrent run already published the same frontend bundle." in publish_step
    assert "git push origin HEAD:main" in publish_step
    assert "git pull --rebase origin main" not in publish_step
    assert "git push --force" not in publish_step
