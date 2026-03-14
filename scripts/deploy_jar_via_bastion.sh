#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/deploy.conf"
JAR_KEY=""
TARGET_FILTER=""
DRY_RUN=false
TARGET_HOP_MODE=""

usage() {
  cat <<'USAGE'
Usage:
  deploy_jar_via_bastion.sh --jar <jar_key|local_jar_path> [--targets "srv-a,srv-b"] [--config /path/to/deploy.conf] [--dry-run]

Options:
  --jar       Required. Jar key in JARS, or direct local jar path.
  --targets   Optional. Comma-separated target names. If omitted, deploys to all targets.
  --config    Optional. Config file path. Default: scripts/deploy.conf
  TARGET_HOP_MODE in config:
              proxy   Local host connects to target via bastion ProxyJump (default, no sshpass needed on bastion).
              bastion Bastion host executes ssh/scp to target (requires sshpass installed on bastion).
              relay   Local logs into bastion, then bastion scp/ssh to target (no bastion sshpass, no port-forwarding).
  --dry-run   Optional. Print commands only, do not execute.
  -h,--help   Show this help.
USAGE
}

log() {
  echo "[$(date '+%F %T')] $*"
}

die() {
  echo "[ERROR] $*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing command: $1"
}

# Safely wrap a string in single quotes for remote shell usage.
sq() {
  local s=${1//\'/\'\"\'\"\'}
  printf "'%s'" "$s"
}

run_cmd() {
  if [ "$DRY_RUN" = true ]; then
    echo "[DRY-RUN] $*"
  else
    eval "$@"
  fi
}

run_on_bastion() {
  local remote_cmd="$1"
  local ssh_cmd
  ssh_cmd="SSHPASS=$(sq "$BASTION_PASS") sshpass -e ssh ${SSH_OPTS[*]} -p $(sq "$BASTION_PORT") $(sq "$BASTION_USER@$BASTION_HOST") $(sq "$remote_cmd")"
  run_cmd "$ssh_cmd"
}

run_on_bastion_with_askpass() {
  local target_pass="$1"
  local remote_inner_cmd="$2"
  local remote_cmd

  remote_cmd="set -euo pipefail; \
TARGET_PASS=$(sq "$target_pass"); \
export TARGET_PASS; \
ASKPASS_FILE=\$(mktemp /tmp/.askpass.XXXXXX); \
trap 'rm -f \"\$ASKPASS_FILE\"' EXIT; \
printf '%s\n' '#!/usr/bin/env bash' 'printf \"%s\n\" \"\$TARGET_PASS\"' > \"\$ASKPASS_FILE\"; \
chmod 700 \"\$ASKPASS_FILE\"; \
DISPLAY=dummy SSH_ASKPASS=\"\$ASKPASS_FILE\" SSH_ASKPASS_REQUIRE=force $remote_inner_cmd"

  run_on_bastion "$remote_cmd"
}

is_target_selected() {
  local target_name="$1"

  if [ -z "$TARGET_FILTER" ]; then
    return 0
  fi

  local item
  IFS=',' read -r -a items <<<"$TARGET_FILTER"
  for item in "${items[@]}"; do
    if [ "$item" = "$target_name" ]; then
      return 0
    fi
  done

  return 1
}

parse_args() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --jar)
        JAR_KEY="${2:-}"
        shift 2
        ;;
      --targets)
        TARGET_FILTER="${2:-}"
        shift 2
        ;;
      --config)
        CONFIG_FILE="${2:-}"
        shift 2
        ;;
      --dry-run)
        DRY_RUN=true
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "Unknown option: $1"
        ;;
    esac
  done

  [ -n "$JAR_KEY" ] || die "--jar is required"
}

load_config() {
  [ -f "$CONFIG_FILE" ] || die "Config file not found: $CONFIG_FILE"
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"

  if ! declare -p JARS >/dev/null 2>&1; then
    JARS=()
  fi
  if ! declare -p TARGETS >/dev/null 2>&1; then
    TARGETS=()
  fi

  : "${BASTION_HOST:?BASTION_HOST is required}"
  : "${BASTION_PORT:=22}"
  : "${BASTION_USER:?BASTION_USER is required}"
  : "${BASTION_PASS:?BASTION_PASS is required}"
  : "${BASTION_STAGING_DIR:=/tmp/jar-staging}"
  : "${TARGET_HOP_MODE:=proxy}"

  if [ "${#JARS[@]}" -eq 0 ] && [ ! -f "$JAR_KEY" ]; then
    die "JARS is empty and --jar is not a local file path"
  fi
  [ "${#TARGETS[@]}" -gt 0 ] || die "TARGETS is empty"
  [ "$TARGET_HOP_MODE" = "proxy" ] || [ "$TARGET_HOP_MODE" = "bastion" ] || [ "$TARGET_HOP_MODE" = "relay" ] || die "TARGET_HOP_MODE must be proxy, bastion or relay"
}

resolve_jar() {
  local row jar_alias local_path remote_name

  if [ -f "$JAR_KEY" ]; then
    JAR_LOCAL_PATH="$JAR_KEY"
    JAR_REMOTE_NAME="$(basename "$JAR_KEY")"
    return 0
  fi

  for row in "${JARS[@]}"; do
    IFS='|' read -r jar_alias local_path remote_name <<<"$row"
    if [ "$jar_alias" = "$JAR_KEY" ]; then
      JAR_LOCAL_PATH="$local_path"
      if [ -n "$remote_name" ] && [ "$remote_name" != "-" ]; then
        JAR_REMOTE_NAME="$remote_name"
      else
        JAR_REMOTE_NAME="$(basename "$local_path")"
      fi
      return 0
    fi
  done

  return 1
}

deploy_to_target() {
  local row="$1"
  local t_name t_host t_port t_user t_pass t_deploy_dir t_runtime_copy_dir t_service_name t_post_cmd
  IFS='|' read -r t_name t_host t_port t_user t_pass t_deploy_dir t_runtime_copy_dir t_service_name t_post_cmd <<<"$row"

  [ -n "$t_name" ] || die "Invalid TARGET entry: missing name"
  [ -n "$t_host" ] || die "Invalid TARGET entry ($t_name): missing host"
  [ -n "$t_port" ] || t_port=22
  [ -n "$t_user" ] || die "Invalid TARGET entry ($t_name): missing user"
  [ -n "$t_pass" ] || die "Invalid TARGET entry ($t_name): missing password"
  [ -n "$t_deploy_dir" ] || die "Invalid TARGET entry ($t_name): missing deploy_dir"

  if ! is_target_selected "$t_name"; then
    log "Skip target $t_name (not in --targets)"
    return
  fi

  local scp_cmd
  if [ "$TARGET_HOP_MODE" = "bastion" ]; then
    log "[$t_name] Step 1/2: distribute jar from bastion to target"
    scp_cmd="set -euo pipefail; SSHPASS=$(sq "$t_pass") sshpass -e scp ${SCP_OPTS[*]} -P $(sq "$t_port") $(sq "$STAGED_JAR_PATH") $(sq "$t_user@$t_host:$t_deploy_dir/$JAR_REMOTE_NAME.new")"
    run_on_bastion "$scp_cmd"
  elif [ "$TARGET_HOP_MODE" = "proxy" ]; then
    [ "$t_pass" = "$BASTION_PASS" ] || die "In proxy mode, target password must match bastion password: $t_name"
    log "[$t_name] Step 1/2: distribute jar to target via bastion ProxyJump"
    scp_cmd="SSHPASS=$(sq "$t_pass") sshpass -e scp ${SCP_OPTS[*]} -o ProxyJump=$(sq "$BASTION_USER@$BASTION_HOST:$BASTION_PORT") -P $(sq "$t_port") $(sq "$JAR_LOCAL_PATH") $(sq "$t_user@$t_host:$t_deploy_dir/$JAR_REMOTE_NAME.new")"
    run_cmd "$scp_cmd"
  else
    log "[$t_name] Step 1/2: distribute jar via bastion relay session"
    scp_cmd="scp ${SCP_OPTS[*]} -o PreferredAuthentications=password -o PubkeyAuthentication=no -P $(sq "$t_port") $(sq "$STAGED_JAR_PATH") $(sq "$t_user@$t_host:$t_deploy_dir/$JAR_REMOTE_NAME.new")"
    run_on_bastion_with_askpass "$t_pass" "$scp_cmd"
  fi

  log "[$t_name] Step 2/2: backup + replace + optional copy + optional restart"
  local target_cmd
  target_cmd="set -euo pipefail; \
mkdir -p $(sq "$t_deploy_dir"); \
if [ -f $(sq "$t_deploy_dir/$JAR_REMOTE_NAME") ]; then cp -f $(sq "$t_deploy_dir/$JAR_REMOTE_NAME") $(sq "$t_deploy_dir/$JAR_REMOTE_NAME.$TIMESTAMP.bak"); fi; \
mv -f $(sq "$t_deploy_dir/$JAR_REMOTE_NAME.new") $(sq "$t_deploy_dir/$JAR_REMOTE_NAME");"

  if [ -n "${t_runtime_copy_dir:-}" ] && [ "$t_runtime_copy_dir" != "-" ]; then
    target_cmd+=" mkdir -p $(sq "$t_runtime_copy_dir"); cp -f $(sq "$t_deploy_dir/$JAR_REMOTE_NAME") $(sq "$t_runtime_copy_dir/$JAR_REMOTE_NAME");"
  fi

  if [ -n "${t_service_name:-}" ] && [ "$t_service_name" != "-" ]; then
    target_cmd+=" systemctl restart $(sq "$t_service_name"); systemctl is-active $(sq "$t_service_name") >/dev/null;"
  fi

  # Run arbitrary post-deploy command on target host (trusted config).
  if [ -n "${t_post_cmd:-}" ] && [ "$t_post_cmd" != "-" ]; then
    target_cmd+=" $t_post_cmd;"
  fi

  local ssh_cmd
  if [ "$TARGET_HOP_MODE" = "bastion" ]; then
    ssh_cmd="set -euo pipefail; SSHPASS=$(sq "$t_pass") sshpass -e ssh ${SSH_OPTS[*]} -p $(sq "$t_port") $(sq "$t_user@$t_host") $(sq "$target_cmd")"
    run_on_bastion "$ssh_cmd"
  elif [ "$TARGET_HOP_MODE" = "proxy" ]; then
    ssh_cmd="SSHPASS=$(sq "$t_pass") sshpass -e ssh ${SSH_OPTS[*]} -o ProxyJump=$(sq "$BASTION_USER@$BASTION_HOST:$BASTION_PORT") -p $(sq "$t_port") $(sq "$t_user@$t_host") $(sq "$target_cmd")"
    run_cmd "$ssh_cmd"
  else
    ssh_cmd="ssh ${SSH_OPTS[*]} -o PreferredAuthentications=password -o PubkeyAuthentication=no -p $(sq "$t_port") $(sq "$t_user@$t_host") $(sq "$target_cmd")"
    run_on_bastion_with_askpass "$t_pass" "$ssh_cmd"
  fi

  log "[$t_name] Done"
}

main() {
  parse_args "$@"

  need_cmd ssh
  need_cmd scp
  need_cmd sshpass

  load_config

  resolve_jar || die "Jar key not found in JARS: $JAR_KEY"
  [ -f "$JAR_LOCAL_PATH" ] || die "Jar file not found: $JAR_LOCAL_PATH"

  TIMESTAMP="$(date '+%Y%m%d%H%M%S')"
  STAGED_JAR_PATH="$BASTION_STAGING_DIR/$JAR_REMOTE_NAME.$TIMESTAMP"

  SSH_OPTS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)
  SCP_OPTS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)

  log "Target hop mode: $TARGET_HOP_MODE"
  if [ "$TARGET_HOP_MODE" = "bastion" ]; then
    log "Check bastion environment"
    run_on_bastion "command -v sshpass >/dev/null 2>&1 || { echo 'sshpass not found on bastion'; exit 1; }"
  fi
  run_on_bastion "mkdir -p $(sq "$BASTION_STAGING_DIR")"

  log "Upload local jar to bastion: $JAR_LOCAL_PATH -> $STAGED_JAR_PATH"
  local upload_cmd
  upload_cmd="SSHPASS=$(sq "$BASTION_PASS") sshpass -e scp ${SCP_OPTS[*]} -P $(sq "$BASTION_PORT") $(sq "$JAR_LOCAL_PATH") $(sq "$BASTION_USER@$BASTION_HOST:$STAGED_JAR_PATH")"
  run_cmd "$upload_cmd"

  local row
  for row in "${TARGETS[@]}"; do
    deploy_to_target "$row"
  done

  if [ "${CLEAN_STAGING_AFTER_DEPLOY:-true}" = "true" ]; then
    log "Cleanup staged jar on bastion: $STAGED_JAR_PATH"
    run_on_bastion "rm -f $(sq "$STAGED_JAR_PATH")"
  fi

  log "All done"
}

main "$@"
