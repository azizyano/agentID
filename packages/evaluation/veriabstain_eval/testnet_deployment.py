"""Application review pin; upstream SDK remains unchanged.

Reviewed from bnb-chain/apex-contracts f6a3c4ff337158a8a66281c565f3f1562e1287b7.
Executable runtime matches the local solc0.8.28/OZ5.4.0 build after UUPS __self
linking and excluding Solidity metadata. All 37 SDK function shapes match.
Evidence: artifacts/testnet/source-verification.json. RPC trust still applies.
"""

from dataclasses import replace

from bnbagent.networks.addresses import get_address

SOURCE_REVISION = "f6a3c4ff337158a8a66281c565f3f1562e1287b7"
REVIEWED_COMMERCE_CODE_HASH = "0xb42935ea4e89b470ea5049cf66d7f1003a5c8d452aef72d78c666577e828380b"
PINNED = replace(get_address(97), commerce_impl="0x55c3826B39a0F671B2C3E5D0F1372CaD0B911421")
