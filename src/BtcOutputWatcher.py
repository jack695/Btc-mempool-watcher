import os
import json
import time
import requests
from typing import Any, Tuple

from .Cache import Cache


class BtcOutputWatcher:
    """
    Watch for Bitcoin transactions that spend specific outputs
    and dump matching transactions to disk.

    Args:
        rpc_user (str): RPC username for Bitcoin Core.
        rpc_password (str): RPC password for Bitcoin Core.
        rpc_host (str): RPC host address.
        rpc_port (int): RPC port number.
        outputs_file (str): Path to the file containing watched txid and output_index pairs.
        dump_folder (str): Path to the folder where transactions will be dumped.
        cache_ttl (int): Time-to-live in seconds for cached transactions.
        fetch_interval (int): Interval in seconds between mempool scans.
    """

    def __init__(
        self,
        rpc_user: str,
        rpc_password: str,
        rpc_host: str = "127.0.0.1",
        rpc_port: int = 8332,
        outputs_file: str = "outputs.txt",
        dump_folder: str = "dumped_txs",
        cache_ttl: int = 3600,
        fetch_interval: int = 180,
    ) -> None:
        self.rpc_user = rpc_user
        self.rpc_password = rpc_password
        self.rpc_host = rpc_host
        self.rpc_port = rpc_port
        self.rpc_url = f"http://{rpc_host}:{rpc_port}"
        self.outputs_file = outputs_file
        self.dump_folder = dump_folder
        self.cache = Cache(default_ttl=cache_ttl)
        self.fetch_interval = fetch_interval
        self.watched_outputs = self._load_watched_outputs()
        os.makedirs(self.dump_folder, exist_ok=True)

    def run(self) -> None:
        """
        Start the watcher loop.
        """

        while True:
            self.watched_outputs = self._load_watched_outputs()
            print(f"Watching {len(self.watched_outputs)} outputs...")

            try:
                self._process_mempool()
            except Exception as e:
                print(f"Error in main loop: {e}")

            print(f"Sleeping for {self.fetch_interval} seconds...")
            time.sleep(self.fetch_interval)

    # === PROTECTED METHODS ===

    def _process_mempool(self) -> None:
        """
        Process all transactions in the mempool.
        """
        txids = self._rpc_call("getrawmempool")
        for txid in txids:
            if txid in self.cache:
                continue

            try:
                raw_tx = self._rpc_call("getrawtransaction", [txid, True])
                if self._tx_spends_watched_outputs(raw_tx):
                    self._dump_transaction(raw_tx)
            except Exception as e:
                print(f"Error fetching transaction {txid}: {e}")

            self.cache.set(txid, True)

        self.cache.cleanup()

    def _load_watched_outputs(self) -> set[Tuple[str, int]]:
        """
        Load watched Bitcoin outputs from a file.

        Returns:
            set[Tuple[str, int]]: Set of (txid, output_index) pairs.

        Raises:
            FileNotFoundError: If the outputs file is missing.
        """
        watched_outputs = set()
        with open(self.outputs_file, "r") as f:
            for line in f:
                if line.strip():
                    txid, output_index = line.strip().split(",")
                    watched_outputs.add((txid, int(output_index)))
        return watched_outputs

    def _rpc_call(self, method: str, params: list[Any] = None) -> Any:
        """
        Make an RPC call to the Bitcoin Core node.

        Args:
            method (str): RPC method name.
            params (list[Any], optional): Method parameters.

        Returns:
            Any: Result from the RPC call.

        Raises:
            RuntimeError: If the RPC call fails.
        """
        payload = json.dumps(
            {
                "jsonrpc": "1.0",
                "id": "watcher",
                "method": method,
                "params": params or [],
            }
        )
        response = requests.post(
            self.rpc_url,
            headers={"content-type": "application/json"},
            data=payload,
            auth=(self.rpc_user, self.rpc_password),
        )

        if response.status_code != 200:
            raise RuntimeError(f"RPC call {method} failed: {response.text}")
        return response.json()["result"]

    def _tx_spends_watched_outputs(self, tx: dict[str, Any]) -> bool:
        """
        Check if a transaction spends any watched outputs (based on txid and output_index).

        Args:
            tx (dict[str, Any]): Transaction data.

        Returns:
            bool: True if the transaction spends any watched outputs, False otherwise.
        """
        # Check inputs (spending transactions)
        for vin in tx.get("vin", []):
            if "txid" in vin and "vout" in vin:
                prev_txid = vin["txid"]
                prev_output_index = vin["vout"]
                if (prev_txid, prev_output_index) in self.watched_outputs:
                    return True
        return False

    def _dump_transaction(self, tx: dict[str, Any]) -> None:
        """
        Dump a transaction to a JSON file.

        Args:
            tx (dict[str, Any]): Transaction data.

        Raises:
            IOError: If the file cannot be written.
        """
        txid = tx.get("txid", "unknown_txid")
        filepath = os.path.join(self.dump_folder, f"{txid}.json")
        with open(filepath, "w") as f:
            json.dump(tx, f, indent=2)
        print(f"Dumped transaction {txid} to {filepath}")
