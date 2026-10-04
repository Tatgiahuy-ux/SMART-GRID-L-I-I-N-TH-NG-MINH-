import hashlib
import json
import time

class Block:
      def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()

      def calculate_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)

      def mine_block(self, difficulty):
        """
        Cơ chế Proof of Work (PoW) - Tìm mã băm bắt đầu bằng chuỗi số 0
        """
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()


class SmartGridBlockchain:
    def __init__(self, difficulty=2):
        """
        Khởi tạo chuỗi khối cho Lưới điện thông minh
        """
        self.chain = [self.create_genesis_block()]
        self.difficulty = difficulty

    def create_genesis_block(self):
        """
        Tạo khối khởi nguyên (Genesis Block) - Khối đầu tiên trong chuỗi
        """
        return Block(0, time.time(), {"info": "Genesis Block - Smart Grid System Init"}, "0")

    def get_latest_block(self):
        """
        Lấy khối mới nhất trong chuỗi
        """
        return self.chain[-1]

    def add_power_data_block(self, consumer_id, actual_usage, predicted_usage):
        """
        Thêm một giao dịch/dữ liệu điện năng mới vào Blockchain
        """
        data = {
            "consumer_id": consumer_id,
            "actual_usage_kwh": actual_usage,
            "predicted_usage_kwh": predicted_usage,
            "recorded_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        }
        
        latest_block = self.get_latest_block()
        new_block = Block(
            index=latest_block.index + 1,
            timestamp=time.time(),
            data=data,
            previous_hash=latest_block.hash
        )
        
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
        return new_block

    def is_chain_valid(self):
        """
        Kiểm tra tính toàn vẹn (Phát hiện dữ liệu có bị giả mạo hay không)
        """
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            if current_block.hash != current_block.calculate_hash():
                print(f"❌ Cảnh báo: Dữ liệu tại Block #{current_block.index} đã bị thay đổi!")
                return False

            if current_block.previous_hash != previous_block.hash:
                print(f"❌ Cảnh báo: Chuỗi bị đứt gãy giữa Block #{previous_block.index} và Block #{current_block.index}!")
                return False

        return True


if __name__ == "__main__":
    print("--- QUY TRÌNH KẾT NỐI BLOCKCHAIN LƯỚI ĐIỆN THÔNG MINH ---")
    
    grid_bc = SmartGridBlockchain(difficulty=2)

    print("\n1. Ghi nhận số liệu điện tiêu thụ vào Blockchain...")
    grid_bc.add_power_data_block(consumer_id="METER_001", actual_usage=120.5, predicted_usage=118.0)
    grid_bc.add_power_data_block(consumer_id="METER_002", actual_usage=85.2, predicted_usage=89.1)

    for block in grid_bc.chain:
        print(f"\n[Block #{block.index}]")
        print(f" Hash: {block.hash}")
        print(f" Prev Hash: {block.previous_hash}")
        print(f" Data: {block.data}")

    print(f"\nCheck tính toàn vẹn chuỗi: {'✅ HỢP LỆ (Không bị giả mạo)' if grid_bc.is_chain_valid() else '❌ BỊ GIẢ MẠO'}")

    print("\n2. Thử nghiệm giả mạo số liệu điện tiêu thụ tại Block #1...")
    grid_bc.chain[1].data["actual_usage_kwh"] = 10.0

    print(f"Check tính toàn vẹn chuỗi sau khi bị chỉnh sửa: {'✅ HỢP LỆ' if grid_bc.is_chain_valid() else '❌ ĐÃ PHÁT HIỆN GIẢ MẠO!'}")