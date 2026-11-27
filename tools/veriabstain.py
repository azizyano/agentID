"""Local entry point for the approved read-only utility. No paid runtime commands."""
import argparse
import importlib.metadata
import json
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/evaluation'))

COMMANDS = {'demo':'run_analysis_demo.py','check':'check_analysis.py','receipts':'receipts.py',
            'diagnose':'diagnose_wallet.py','compat':'check_wallet_compatibility.py',
            'compat-ui':'serve_wallet_compatibility.py'}


def doctor():
    """Read local package versions and frozen fixture integrity, never credentials."""
    dependencies = {}
    for name in ('pydantic','web3','bnbagent'):
        try:
            dependencies[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            dependencies[name] = None
    manifest_ok = False
    manifest_digest = None
    try:
        from veriabstain_eval.dataset import load_manifest
        _, manifest_digest = load_manifest()
        manifest_ok = True
    except Exception:
        pass
    ready = sys.version_info[:2] == (3,12) and all(dependencies.values()) and manifest_ok
    return {'status':'LOCAL_SETUP_READY' if ready else 'LOCAL_SETUP_INCOMPLETE',
            'python':'.'.join(map(str,sys.version_info[:3])), 'dependencies':dependencies,
            'fixture_manifest_intact':manifest_ok,'fixture_manifest_sha256':manifest_digest,
            'scope':'READ_ONLY_VALIDATION_UTILITY','original_value_gate':'NOT_PASSED',
            'network_calls':0,'model_calls':0,'transactions':0,
            'limitations':'Installed versions and fixture integrity only; no live RPC, full source attestation or production-readiness check'}


def main(argv=None, *, runner=runpy.run_path):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__, epilog=(
        'Commands: doctor (offline setup), demo (offline SDK composition), '
        'check --authorization FILE --analysis FILE (public read-only RPC), '
        'receipts [--id ID] (offline receipt inspection), diagnose --prompt or --report FILE (wallet issue handoff), '
        'compat --case FILE [--baseline FILE] [--format markdown] (offline wallet compatibility), '
        'compat-ui (local browser workspace).'))
    parser.add_argument('command',nargs='?',choices=['doctor',*COMMANDS])
    # Remaining arguments belong to the chosen existing CLI, including --help.
    if not argv or argv[0] in ('-h','--help'):
        parser.print_help()
        return 0
    args = parser.parse_args(argv[:1])
    if args.command == 'doctor':
        if len(argv) != 1:
            print(json.dumps({'status':'INVALID_ARGUMENTS'}),file=sys.stderr)
            return 2
        report = doctor()
        print(json.dumps(report,indent=2))
        return 0 if report['status']=='LOCAL_SETUP_READY' else 2
    previous = sys.argv
    script = ROOT/'tools'/COMMANDS[args.command]
    try:
        sys.argv = [str(script),*argv[1:]]
        runner(str(script),run_name='__main__')
        return 0
    except SystemExit as error:
        return error.code if type(error.code) is int else (0 if error.code is None else 1)
    finally:
        sys.argv = previous


if __name__=='__main__':
    raise SystemExit(main())
