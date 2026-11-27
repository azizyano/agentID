import json
import runpy
import sys
from pathlib import Path

import pytest

ENTRY = runpy.run_path(str(Path(__file__).resolve().parents[2]/'tools/veriabstain.py'))


def test_help_has_no_side_effects(capsys):
    assert ENTRY['main']([],runner=lambda *_args,**_kwargs:pytest.fail('Unexpected dispatch'))==0
    assert 'doctor' in capsys.readouterr().out


@pytest.mark.parametrize('command,script',[
    ('demo','run_analysis_demo.py'), ('check','check_analysis.py'),
    ('receipts','receipts.py'), ('diagnose','diagnose_wallet.py'),
    ('compat','check_wallet_compatibility.py'),
])
def test_dispatch_forwards_without_shell_and_restores_argv(command,script):
    before=sys.argv
    calls=[]
    def runner(path,run_name):
        calls.append((Path(path).name,list(sys.argv),run_name))
        raise SystemExit(2)
    assert ENTRY['main']([command,'--help'],runner=runner)==2
    assert calls[0][0]==script and calls[0][1][1:]==['--help']
    assert sys.argv is before


def test_doctor_reports_local_checks_only(capsys):
    status=ENTRY['main'](['doctor'])
    report=json.loads(capsys.readouterr().out)
    assert status==0 and report['status']=='LOCAL_SETUP_READY'
    assert report['fixture_manifest_intact']
    assert report['network_calls']==report['model_calls']==report['transactions']==0
    assert report['original_value_gate']=='NOT_PASSED'


def test_unknown_command_cannot_dispatch():
    with pytest.raises(SystemExit):
        ENTRY['main'](['paid-model'],runner=lambda *_args,**_kwargs:pytest.fail('Unexpected dispatch'))
