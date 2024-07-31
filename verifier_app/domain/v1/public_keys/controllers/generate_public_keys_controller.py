import hashlib
import pickle

from bitcoinutils.keys import PrivateKey, PublicKey
from bitcoinutils.setup import NETWORK

from bitvmx_protocol_library.bitvmx_protocol_definition.entities.bitvmx_protocol_properties_dto import (
    BitVMXProtocolPropertiesDTO,
)
from bitvmx_protocol_library.bitvmx_protocol_definition.entities.bitvmx_protocol_setup_properties_dto import (
    BitVMXProtocolSetupPropertiesDTO,
)
from bitvmx_protocol_library.bitvmx_protocol_definition.entities.bitvmx_prover_winternitz_public_keys_dto import (
    BitVMXProverWinternitzPublicKeysDTO,
)
from bitvmx_protocol_library.enums import BitcoinNetwork


class GeneratePublicKeysController:

    def __init__(self, generate_verifier_public_keys_service_class):
        self.generate_verifier_public_keys_service_class = (
            generate_verifier_public_keys_service_class
        )

    async def __call__(
        self,
        setup_uuid: str,
        unspendable_public_key_hex: str,
        public_keys_post_view_input,
        bitvmx_protocol_properties_dto: BitVMXProtocolPropertiesDTO,
        bitvmx_protocol_setup_properties_dto: BitVMXProtocolSetupPropertiesDTO,
        bitvmx_prover_winternitz_public_keys_dto: BitVMXProverWinternitzPublicKeysDTO,
    ):
        with open(f"verifier_files/{setup_uuid}/file_database.pkl", "rb") as f:
            protocol_dict = pickle.load(f)
        if protocol_dict["network"] == BitcoinNetwork.MUTINYNET:
            assert NETWORK == "testnet"
        else:
            assert NETWORK == protocol_dict["network"].value
        verifier_private_key = PrivateKey(b=bytes.fromhex(protocol_dict["verifier_private_key"]))

        protocol_dict["verifier_public_key"] = verifier_private_key.get_public_key().to_hex()

        if verifier_private_key.get_public_key().to_x_only_hex() not in unspendable_public_key_hex:
            raise Exception("Seed does not contain public key")

        destroyed_public_key_hex = hashlib.sha256(
            bytes.fromhex(unspendable_public_key_hex)
        ).hexdigest()
        destroyed_public_key = PublicKey(hex_str="02" + destroyed_public_key_hex)
        protocol_dict["seed_destroyed_public_key_hex"] = unspendable_public_key_hex
        protocol_dict["destroyed_public_key"] = destroyed_public_key.to_hex()
        protocol_dict["prover_public_key"] = public_keys_post_view_input.prover_public_key
        protocol_dict["bitvmx_prover_winternitz_public_keys_dto"] = (
            bitvmx_prover_winternitz_public_keys_dto
        )
        protocol_dict["bitvmx_protocol_setup_properties_dto"] = bitvmx_protocol_setup_properties_dto
        protocol_dict["bitvmx_protocol_properties_dto"] = bitvmx_protocol_properties_dto

        protocol_dict["controlled_prover_address"] = (
            public_keys_post_view_input.controlled_prover_address
        )

        generate_verifier_public_keys_service = self.generate_verifier_public_keys_service_class(
            verifier_private_key
        )
        bitvmx_verifier_winternitz_public_keys_dto = generate_verifier_public_keys_service(
            bitvmx_protocol_properties_dto=bitvmx_protocol_properties_dto
        )
        protocol_dict["bitvmx_verifier_winternitz_public_keys_dto"] = (
            bitvmx_verifier_winternitz_public_keys_dto
        )

        protocol_dict["public_keys"] = [
            protocol_dict["verifier_public_key"],
            protocol_dict["prover_public_key"],
        ]

        with open(f"verifier_files/{setup_uuid}/file_database.pkl", "wb") as f:
            pickle.dump(protocol_dict, f)

        return (
            bitvmx_verifier_winternitz_public_keys_dto,
            verifier_private_key.get_public_key().to_hex(),
        )
