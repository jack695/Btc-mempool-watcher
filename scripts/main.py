from src.BtcOutputWatcher import BtcOutputWatcher

if __name__ == "__main__":
    watcher = BtcOutputWatcher(
        rpc_user="USERNAME",
        rpc_password="PASSWORD",
        rpc_host="127.0.0.1",
        rpc_port=8332,
        outputs_file="./data/outputs.txt",  # File with txid, output_index pairs
        dump_folder="./data/dumped_txs",
        cache_ttl=3600,
        fetch_interval=1,
    )
    watcher.run()
