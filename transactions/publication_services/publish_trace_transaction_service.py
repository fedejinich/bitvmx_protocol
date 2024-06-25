from bitcoinutils.keys import PublicKey
from bitcoinutils.transactions import TxWitnessInput
from bitcoinutils.utils import ControlBlock

from mutinyet_api.services.broadcast_transaction_service import BroadcastTransactionService
from mutinyet_api.services.transaction_info_service import TransactionInfoService
from scripts.services.execution_trace_script_generator_service import (
    ExecutionTraceScriptGeneratorService,
)
from winternitz_keys_handling.services.generate_witness_from_input_nibbles_service import (
    GenerateWitnessFromInputNibblesService,
)
from winternitz_keys_handling.services.generate_witness_from_input_single_word_service import (
    GenerateWitnessFromInputSingleWordService,
)


class PublishTraceTransactionService:

    def __init__(self, prover_private_key):
        self.execution_trace_script_generator_service = ExecutionTraceScriptGeneratorService()
        self.generate_prover_witness_from_input_single_word_service = (
            GenerateWitnessFromInputSingleWordService(prover_private_key)
        )
        self.generate_witness_from_input_nibbles_service = GenerateWitnessFromInputNibblesService(
            prover_private_key
        )
        self.broadcast_transaction_service = BroadcastTransactionService()
        self.transaction_info_service = TransactionInfoService()

    def __call__(self, protocol_dict):
        trace_words_lengths = protocol_dict["trace_words_lengths"]
        amount_of_wrong_step_search_iterations = protocol_dict[
            "amount_of_wrong_step_search_iterations"
        ]
        amount_of_bits_wrong_step_search = protocol_dict["amount_of_bits_wrong_step_search"]
        amount_of_bits_per_digit_checksum = protocol_dict["amount_of_bits_per_digit_checksum"]
        destroyed_public_key = PublicKey(hex_str=protocol_dict["destroyed_public_key"])
        choice_search_prover_public_keys_list = protocol_dict[
            "choice_search_prover_public_keys_list"
        ]
        choice_search_verifier_public_keys_list = protocol_dict[
            "choice_search_verifier_public_keys_list"
        ]

        trace_array = []
        for word_length in trace_words_lengths:
            trace_array.append("1" * word_length)

        trace_witness = []

        previous_choice_tx = protocol_dict["search_choice_tx_list"][-1].get_txid()
        previous_choice_transaction_info = self.transaction_info_service(previous_choice_tx)
        previous_witness = previous_choice_transaction_info.inputs[0].witness
        trace_witness += previous_witness[0:4]
        current_choice = int(previous_witness[1])

        trace_witness += self.generate_prover_witness_from_input_single_word_service(
            step=(3 + (amount_of_wrong_step_search_iterations - 1) * 2 + 1),
            case=0,
            input_number=current_choice,
            amount_of_bits=amount_of_bits_wrong_step_search,
        )

        for word_count in range(len(trace_words_lengths)):

            input_number = []
            for letter in trace_array[len(trace_array) - word_count - 1]:
                input_number.append(int(letter, 16))

            trace_witness += self.generate_witness_from_input_nibbles_service(
                step=3 + amount_of_wrong_step_search_iterations * 2,
                case=len(trace_words_lengths) - word_count - 1,
                input_numbers=input_number,
                bits_per_digit_checksum=amount_of_bits_per_digit_checksum,
            )

        trace_tx = protocol_dict["trace_tx"]
        trace_prover_public_keys = protocol_dict["trace_prover_public_keys"]

        trace_script = self.execution_trace_script_generator_service(
            trace_prover_public_keys,
            trace_words_lengths,
            amount_of_bits_per_digit_checksum,
            amount_of_bits_wrong_step_search,
            choice_search_prover_public_keys_list[-1][0],
            choice_search_verifier_public_keys_list[-1][0],
        )
        trace_script_address = destroyed_public_key.get_taproot_address([[trace_script]])

        trace_control_block = ControlBlock(
            destroyed_public_key,
            scripts=[[trace_script]],
            index=0,
            is_odd=trace_script_address.is_odd(),
        )

        trace_tx.witnesses.append(
            TxWitnessInput(
                trace_witness
                + [
                    # third_signature_bob,
                    # third_signature_alice,
                    trace_script.to_hex(),
                    trace_control_block.to_hex(),
                ]
            )
        )

        self.broadcast_transaction_service(transaction=trace_tx.serialize())
        print("Trace transaction: " + trace_tx.get_txid())
        return trace_tx
