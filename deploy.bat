@echo off
REM Azure AI Single-Command Deployer Launcher
REM Usage:
REM   deploy "deploy a python fastapi app to dev"
REM   deploy --interactive
REM   deploy --web
REM   deploy --dry-run "deploy everything"

set SCRIPT_DIR=%~dp0
python "%SCRIPT_DIR%ai_agents\deploy_cli.py" %*
