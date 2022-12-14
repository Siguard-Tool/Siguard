import json
import binascii

from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Tuple

from siguard.concolic.concrete_data import ConcreteData

from siguard.disassembler.disassembly import Disassembly
from siguard.laser.ethereum.svm import LaserEVM
from siguard.laser.ethereum.state.world_state import WorldState
from siguard.laser.ethereum.state.account import Account
from siguard.laser.ethereum.transaction.concolic import execute_transaction
from siguard.laser.plugin.loader import LaserPluginLoader
from siguard.laser.smt import Expression, BitVec, symbol_factory
from siguard.laser.ethereum.transaction.transaction_models import tx_id_manager
from siguard.plugin.discovery import PluginDiscovery


def setup_concrete_initial_state(concrete_data: ConcreteData) -> WorldState:
    """
    Sets up concrete initial state
    :param concrete_data: Concrete data
    :return: initialised world state
    """
    world_state = WorldState()
    for address, details in concrete_data["initialState"]["accounts"].items():
        account = Account(address, concrete_storage=True)
        account.code = Disassembly(details["code"][2:])
        account.nonce = details["nonce"]
        if type(details["storage"]) == str:
            details["storage"] = eval(details["storage"])  # type: ignore
        for key, value in details["storage"].items():
            key_bitvec = symbol_factory.BitVecVal(int(key, 16), 256)
            account.storage[key_bitvec] = symbol_factory.BitVecVal(int(value, 16), 256)

        world_state.put_account(account)
        account.set_balance(int(details["balance"], 16))
    return world_state


def concrete_execution(concrete_data: ConcreteData) -> Tuple[WorldState, List]:
    """
    Executes code concretely to find the path to be followed by concolic executor
    :param concrete_data: Concrete data
    :return: path trace
    """
    tx_id_manager.restart_counter()
    init_state = setup_concrete_initial_state(concrete_data)
    laser_evm = LaserEVM(execution_timeout=1000)
    laser_evm.open_states = [deepcopy(init_state)]
    plugin_loader = LaserPluginLoader()
    assert PluginDiscovery().is_installed("myth_concolic_execution")
    trace_plugin = PluginDiscovery().installed_plugins["myth_concolic_execution"]()

    plugin_loader.load(trace_plugin)
    laser_evm.time = datetime.now()
    plugin_loader.instrument_virtual_machine(laser_evm, None)
    for transaction in concrete_data["steps"]:
        execute_transaction(
            laser_evm,
            callee_address=transaction["address"],
            caller_address=symbol_factory.BitVecVal(
                int(transaction["origin"], 16), 256
            ),
            origin_address=symbol_factory.BitVecVal(
                int(transaction["origin"], 16), 256
            ),
            gas_limit=int(transaction.get("gasLimit", "0x9999999999999999999999"), 16),
            data=binascii.a2b_hex(transaction["input"][2:]),
            gas_price=int(transaction.get("gasPrice", "0x773594000"), 16),
            value=int(transaction["value"], 16),
            track_gas=False,
        )

    tx_id_manager.restart_counter()
    return init_state, plugin_loader.plugin_list["MythX Trace Finder"].tx_trace  # type: ignore
