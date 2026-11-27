"""Compare one expected BSC contract call with one saved wallet observation."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .workers import strict_json

MAX_REPORT_BYTES = 16_384
MAX_TIMESTAMP = 253_402_300_799

Address = Annotated[str, Field(pattern=r"^0x[0-9a-fA-F]{40}$")]
Calldata = Annotated[str, Field(pattern=r"^0x(?:[0-9a-fA-F]{2}){4,2048}$")]
FunctionSelector = Annotated[str, Field(pattern=r"^0x[0-9a-fA-F]{8}$")]
Wei = Annotated[int, Field(ge=0, le=2**256 - 1)]
Timestamp = Annotated[int, Field(ge=0, le=MAX_TIMESTAMP)]
WalletSurface = Literal["binance_dapp_browser", "binance_ai_pro", "binance_agentic_cli"]


class CallRequirements(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    chain_id: Annotated[int, Field(ge=56, le=56)]
    surface: WalletSurface
    target: Address
    native_value_wei: Annotated[int, Field(ge=0, le=0)]
    requires_wallet_fee: bool
    requires_app_confirmation: bool


class ExpectedCall(CallRequirements):
    sender: Address
    calldata: Calldata
    max_observation_age_seconds: Annotated[int, Field(gt=0)]


class PartialExpectedCall(CallRequirements):
    sender: Address | None = None
    calldata: Calldata | None = None
    function_selector: FunctionSelector | None = None
    max_observation_age_seconds: Annotated[int, Field(gt=0)] | None = None

    @model_validator(mode="after")
    def check_selector(self):
        if (
            self.function_selector is not None
            and self.calldata is not None
            and self.function_selector.lower() != self.calldata[:10].lower()
        ):
            raise ValueError("The selector conflicts with the expected calldata")
        return self


class WalletObservation(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    evidence: Literal["FIXTURE", "USER_REPORTED"]
    surface: WalletSurface | Literal["unknown"]
    stage: Literal["wallet_selected", "preview_passed", "preview_blocked", "unknown"]
    observed_at: Timestamp | None = None
    preview_expires_at: Timestamp | None = None
    chain_id: Annotated[int, Field(gt=0)] | None = None
    sender: Address | None = None
    target: Address | None = None
    calldata: Calldata | None = None
    native_value_wei: Wei | None = None
    wallet_fee_wei: Wei | None = None
    app_confirmation_required: bool | None = None
    risk_findings: Literal["clear", "warning"] | None = None


class CompatibilityCase(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    schema_version: Annotated[int, Field(ge=1, le=1)]
    expected: ExpectedCall
    observation: WalletObservation


class PreviewReportObservation(WalletObservation):
    wallet_fee_displayed: bool | None = None
    developer_mode_enabled: bool | None = None

    @model_validator(mode="after")
    def check_fee_fields(self):
        if self.wallet_fee_displayed is False and self.wallet_fee_wei is not None:
            raise ValueError("A fee amount conflicts with an explicitly absent display")
        return self


class PreviewReportCase(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    schema_version: Annotated[int, Field(ge=2, le=2)]
    expected: PartialExpectedCall
    observation: PreviewReportObservation


def parse_compatibility_case(raw: bytes) -> CompatibilityCase | PreviewReportCase:
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError("Case exceeds the size limit")
    payload = strict_json(raw.decode("utf-8-sig"))
    if isinstance(payload, dict) and payload.get("schema_version") == 2:
        return PreviewReportCase.model_validate(payload)
    return CompatibilityCase.model_validate(payload)


def _compare(expected, observed):
    if expected is None or observed is None:
        return "UNKNOWN"
    if isinstance(expected, str):
        expected, observed = expected.lower(), observed.lower()
    return "MATCH" if expected == observed else "MISMATCH"


def check_compatibility(case: CompatibilityCase | PreviewReportCase, now: int) -> dict:
    """Report only evidence scoped to this action, without granting permission."""
    if type(now) is not int or not 0 <= now <= MAX_TIMESTAMP:
        raise ValueError("Invalid evaluation time")
    expected, observation = case.expected, case.observation
    checks = {
        name: _compare(getattr(expected, name), getattr(observation, name))
        for name in ("chain_id", "sender")
    }
    preview_observed = observation.stage in ("preview_passed", "preview_blocked")
    checks.update({
        name: _compare(getattr(expected, name), getattr(observation, name)) if preview_observed else "UNKNOWN"
        for name in ("target", "calldata", "native_value_wei")
    })
    reported_surface = None if observation.surface == "unknown" else observation.surface
    checks["wallet_surface"] = _compare(expected.surface, reported_surface)
    if isinstance(observation, PreviewReportObservation) and observation.developer_mode_enabled is not None:
        checks["developer_mode"] = "ENABLED" if observation.developer_mode_enabled else "DISABLED"
    checks["simulation"] = "PASSED" if observation.stage == "preview_passed" else "UNKNOWN"
    checks["observation_age"] = "UNKNOWN"
    if observation.observed_at is not None:
        age = now - observation.observed_at
        age_limit = expected.max_observation_age_seconds
        if age < 0:
            checks["observation_age"] = "FUTURE"
        elif age_limit is not None:
            checks["observation_age"] = "STALE" if age > age_limit else "FRESH"

    checks["preview_expiry"] = "UNKNOWN"
    if observation.preview_expires_at is not None:
        checks["preview_expiry"] = "EXPIRED" if now >= observation.preview_expires_at else "FRESH"
    checks["wallet_fee"] = "UNKNOWN" if expected.requires_wallet_fee else "NOT_REQUIRED"
    checks["app_confirmation"] = "UNKNOWN" if expected.requires_app_confirmation else "NOT_REQUIRED"
    checks["risk_review"] = "UNKNOWN"
    if observation.stage == "preview_passed":
        if expected.requires_wallet_fee and observation.wallet_fee_wei is not None:
            checks["wallet_fee"] = "MATCH"
        if (
            expected.requires_wallet_fee
            and isinstance(observation, PreviewReportObservation)
            and observation.wallet_fee_displayed is False
        ):
            checks["wallet_fee"] = "MISMATCH"
        if expected.requires_app_confirmation:
            checks["app_confirmation"] = _compare(True, observation.app_confirmation_required)
        if observation.risk_findings is not None:
            checks["risk_review"] = observation.risk_findings.upper()

    # Wallet selection alone can establish a mismatch. Preview-only fields
    # from a separate or unsupported stage cannot establish compatibility.
    if observation.stage == "preview_blocked":
        result = "BLOCKED_BY_WALLET"
    elif (
        observation.stage == "preview_passed"
        and observation.surface in ("binance_ai_pro", "binance_agentic_cli")
        and checks.get("developer_mode") == "DISABLED"
    ):
        result = "INCONCLUSIVE"
    elif checks["observation_age"] != "FRESH" or (
        observation.stage == "preview_passed" and checks["preview_expiry"] != "FRESH"
    ):
        result = "INCONCLUSIVE"
    elif observation.stage not in ("wallet_selected", "preview_passed"):
        result = "INCONCLUSIVE"
    elif checks["risk_review"] == "WARNING":
        result = "INCONCLUSIVE"
    elif "MISMATCH" in checks.values():
        result = "INCOMPATIBLE"
    elif observation.stage == "preview_passed" and "UNKNOWN" not in checks.values():
        result = "PREVIEW_MATCHED"
    else:
        result = "INCONCLUSIVE"

    return {
        "schema_version": 1,
        "status": result,
        "evidence": observation.evidence,
        "expected_wallet_surface": expected.surface,
        "wallet_surface": observation.surface,
        "reported_stage": observation.stage,
        "observed_at": observation.observed_at,
        "evaluated_at": now,
        "checks": checks,
        "execution_authorized": False,
        "submission_verified": False,
    }


_CHECK_LABELS = {
    "chain_id": "Chain",
    "sender": "Selected sender",
    "target": "Target contract",
    "calldata": "Exact calldata",
    "native_value_wei": "Native value",
    "wallet_surface": "Wallet surface",
    "developer_mode": "Developer Mode",
    "simulation": "Simulation",
    "observation_age": "Observation age",
    "preview_expiry": "Preview expiry",
    "wallet_fee": "Wallet-displayed fee",
    "app_confirmation": "Separate Binance App approval",
    "risk_review": "Wallet risk findings",
}


def _expected_selector(expected: ExpectedCall | PartialExpectedCall) -> str | None:
    if expected.calldata is not None:
        return expected.calldata[:10].lower()
    if isinstance(expected, PartialExpectedCall) and expected.function_selector is not None:
        return expected.function_selector.lower()
    return None


def public_action(expected: ExpectedCall | PartialExpectedCall) -> dict:
    return {
        "chain_id": expected.chain_id,
        "wallet_surface": expected.surface,
        "target": expected.target,
        "function_selector": _expected_selector(expected),
        "native_value_wei": expected.native_value_wei,
    }


def compare_compatibility(
    baseline: CompatibilityCase | PreviewReportCase,
    current: CompatibilityCase | PreviewReportCase,
    *,
    baseline_now: int,
    current_now: int,
) -> dict:
    """Compare saved attempts for the same expected workflow and evidence class."""
    before, after = baseline.expected, current.expected
    selector = _expected_selector(after)
    if (
        selector is None
        or _expected_selector(before) != selector
        or any(
            _compare(getattr(before, name), getattr(after, name)) != "MATCH"
            for name in CallRequirements.model_fields
        )
    ):
        raise ValueError("Comparison requires the same expected workflow and review policy")
    if baseline.observation.evidence != current.observation.evidence:
        raise ValueError("Comparison requires the same evidence class")

    input_checks = {
        name: _compare(getattr(before, name), getattr(after, name))
        for name in ("sender", "calldata", "max_observation_age_seconds")
    }
    if "MISMATCH" in input_checks.values():
        raise ValueError("Known expected inputs or age limits differ")

    if baseline_now > current_now:
        raise ValueError("The baseline evaluation must precede or equal the later evaluation")
    before_at = baseline.observation.observed_at
    after_at = current.observation.observed_at
    order = "SUPPLIED"
    if before_at is not None and after_at is not None:
        if before_at > after_at:
            raise ValueError("The baseline observation is later than the comparison observation")
        if before_at < after_at:
            order = "TIMESTAMPS_CAPTURED"

    return {
        "schema_version": 1,
        "status": "COMPARED",
        "expected_action": public_action(after),
        "expected_input_checks": input_checks,
        "observation_order": order,
        "before": check_compatibility(baseline, baseline_now),
        "after": check_compatibility(current, current_now),
        "execution_authorized": False,
        "submission_verified": False,
    }


def _utc_time(timestamp: int | None) -> str:
    if timestamp is None:
        return "Unknown"
    return (datetime(1970, 1, 1, tzinfo=UTC) + timedelta(seconds=timestamp)).isoformat()


def render_compatibility_markdown(
    case: CompatibilityCase | PreviewReportCase, report: dict
) -> str:
    """Export the checks and action identifiers, omitting the sender and call arguments."""
    expected = case.expected
    selector = _expected_selector(expected)
    action = f"BNB Smart Chain (56), contract `{expected.target}`, 0 wei"
    if selector is not None:
        action += f", selector `{selector}`"
    lines = [
        "# VeriAbstain compatibility report",
        "",
        f"- Result: `{report['status']}`",
        f"- Evidence: `{report['evidence']}`",
        f"- Expected action: {action}",
        f"- Expected wallet surface: `{report['expected_wallet_surface']}`",
        f"- Reported wallet surface: `{report['wallet_surface']}`",
        f"- Reported stage: `{report['reported_stage']}`",
        f"- Observed at: {_utc_time(report['observed_at'])}",
        f"- Preview expires at: {_utc_time(case.observation.preview_expires_at)}",
        f"- Evaluated at: {_utc_time(report['evaluated_at'])}",
        "",
        "| Check | Result |",
        "| --- | --- |",
    ]
    for name, result in report["checks"].items():
        lines.append(f"| {_CHECK_LABELS[name]} | `{result}` |")
    lines.append("")
    if report["checks"]["wallet_fee"] == "MISMATCH":
        lines.append("The preview reportedly displayed no fee. The fee amount is unknown.")
    if report["checks"]["app_confirmation"] == "MISMATCH":
        lines.append("The workflow required separate App approval. The preview reported `requireConfirmation: false`.")
    lines.extend(["", "Execution authorized: false. Submission verified: false."])
    return "\n".join(lines)


def render_comparison_markdown(comparison: dict) -> str:
    action = comparison["expected_action"]
    before, after = comparison["before"], comparison["after"]
    lines = [
        "# VeriAbstain before-and-after report",
        "",
        f"- Expected action: BNB Smart Chain ({action['chain_id']}), contract `{action['target']}`, "
        f"selector `{action['function_selector']}`, {action['native_value_wei']} wei",
        f"- Expected wallet surface: `{action['wallet_surface']}`",
        f"- Evidence: `{before['evidence']}`",
        "",
        "| Check | Before | After |",
        "| --- | --- | --- |",
        f"| Assessment | `{before['status']}` | `{after['status']}` |",
        f"| Reported stage | `{before['reported_stage']}` | `{after['reported_stage']}` |",
        f"| Observed at | {_utc_time(before['observed_at'])} | {_utc_time(after['observed_at'])} |",
        f"| Evaluated at | {_utc_time(before['evaluated_at'])} | {_utc_time(after['evaluated_at'])} |",
    ]
    for name, label in _CHECK_LABELS.items():
        if name in before["checks"] or name in after["checks"]:
            before_check = before["checks"].get(name, "UNKNOWN")
            after_check = after["checks"].get(name, "UNKNOWN")
            lines.append(f"| {label} | `{before_check}` | `{after_check}` |")
    lines.extend(["", "| Expected input across both attempts | Comparison |", "| --- | --- |"])
    expected_labels = {
        "sender": "Sender",
        "calldata": "Full calldata",
        "max_observation_age_seconds": "Age limit",
    }
    for name, label in expected_labels.items():
        lines.append(f"| {label} | `{comparison['expected_input_checks'][name]}` |")
    lines.append("")
    if comparison["observation_order"] == "SUPPLIED":
        lines.append("Attempt order comes from the supplied cases. Observation timestamps do not establish it.")
        lines.append("")
    lines.append("Execution authorized: false. Submission verified: false.")
    return "\n".join(lines)
