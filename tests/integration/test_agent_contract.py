import socket
import ssl

import pytest

from veriabstain_eval.agent_contract import check_evidence_contract,assert_evidence_contract
from veriabstain_eval.deterministic_baseline import assess_baseline
from veriabstain_eval.evidence_envelope import assess_envelope


def test_existing_checker_can_be_used_directly_in_pytest():
    report=assert_evidence_contract(assess_baseline)
    assert report['cases']==report['passed']==62 and report['failed']==0
    assert report['blocked_network_attempts']==0 and report['assurance']=='SIMULATED_READ'


def test_existing_pydantic_checker_needs_no_output_adapter():
    assert assert_evidence_contract(assess_envelope)['passed']==62


def test_worker_sees_inputs_and_time_only():
    def checker(package,*,now):
        assert 'expected' not in package and 'case_id' not in package
        assert type(now) is int
        return assess_baseline(package,now=now)
    assert assert_evidence_contract(checker)['passed']==62


def test_caught_network_attempt_still_fails_case_and_guard_restores():
    original=socket.getaddrinfo
    def checker(package,*,now):
        try:socket.getaddrinfo('unused.invalid',443)
        except RuntimeError:pass
        return assess_baseline(package,now=now)
    report=check_evidence_contract(checker)
    assert report['failed']==62 and report['blocked_network_attempts']==62
    assert all(row['network_attempted'] for row in report['results'])
    assert socket.getaddrinfo is original


@pytest.mark.parametrize('method',['send','sendall','recv','gethostbyname','tls_write'])
def test_existing_io_and_alternative_dns_attempts_are_counted(method):
    sock=socket.socket()
    before_send=socket.socket.send;before_tls=ssl.SSLSocket.write
    try:
        def checker(package,*,now):
            try:
                if method=='gethostbyname':socket.gethostbyname('unused.invalid')
                elif method=='tls_write':ssl.SSLSocket.write(None,b'data')
                elif method=='recv':sock.recv(1)
                else:getattr(sock,method)(b'data')
            except RuntimeError:pass
            return assess_baseline(package,now=now)
        report=check_evidence_contract(checker)
        assert report['blocked_network_attempts']==62 and report['failed']==62
        assert socket.socket.send is before_send and ssl.SSLSocket.write is before_tls
    finally:sock.close()


def test_input_mutation_cannot_pass_even_with_correct_return():
    def checker(package,*,now):
        result=assess_baseline(package,now=now)
        package['claim']['value']='changed'
        return result
    report=check_evidence_contract(checker)
    assert report['failed']==62 and all(not row['input_unchanged'] for row in report['results'])


def test_raw_exception_and_unknown_output_never_leak():
    def broken(*_args,**_kwargs):raise ValueError('confidential-api-key')
    report=check_evidence_contract(broken)
    assert report['failed']==62 and 'confidential' not in str(report)
    with pytest.raises(AssertionError) as error:assert_evidence_contract(broken)
    assert 'confidential' not in str(error.value)
    def unknown(*_args,**_kwargs):return {'snapshot_status':'confidential-api-key','execution_authorized':0}
    report=check_evidence_contract(unknown)
    assert 'confidential' not in str(report)
    assert all(row['actual']['execution_authorized'] is None for row in report['results'])


def test_async_checker_is_rejected_without_running_its_body():
    invoked=[]
    async def checker(*_args,**_kwargs):invoked.append(True)
    report=check_evidence_contract(checker)
    assert report['failed']==62 and invoked==[]
    assert all(row['error']=='ASYNC_CHECKER_UNSUPPORTED' for row in report['results'])


def test_noncallable_rejected():
    with pytest.raises(TypeError):check_evidence_contract(None)
