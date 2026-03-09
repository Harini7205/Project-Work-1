import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random

# Hospital Node
class HospitalNode:
    def __init__(self, node_id):
        self.node_id = node_id
        self.success_rate = 0.9

    def update_metrics(self):
        self.throughput = random.uniform(50, 150)
        self.latency = random.uniform(10, 200)
        self.cpu = random.uniform(10, 90)

    def perform_task(self):
        return random.random() < self.success_rate


# DQN Network
class DQN(nn.Module):
    def __init__(self, state_size, action_size):
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(state_size, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, action_size)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)


# RL Agent
class RLAgent:
    def __init__(self, state_size, action_size):
        self.model = DQN(state_size, action_size)
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        self.loss_fn = nn.MSELoss()
        self.gamma = 0.95
        self.epsilon = 0.3

    def select_action(self, state):
        if random.random() < self.epsilon:
            action = random.randint(0, 3)
            print("Random exploration chosen")
            return action

        with torch.no_grad():
            state_tensor = torch.FloatTensor(state)
            q_values = self.model(state_tensor)
            action = torch.argmax(q_values).item()
            print("AI exploitation chosen")
            return action

    def train(self, state, action, reward, next_state):
        state = torch.FloatTensor(state)
        next_state = torch.FloatTensor(next_state)

        q_values = self.model(state)
        next_q_values = self.model(next_state)

        target = q_values.clone().detach()
        target[action] = reward + self.gamma * torch.max(next_q_values)

        loss = self.loss_fn(q_values, target)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()


# Helper Functions
def get_state(nodes):
    state = []
    for node in nodes:
        state.extend([
            node.throughput,
            node.latency,
            node.cpu,
            node.success_rate
        ])
    return np.array(state, dtype=np.float32)


def compute_reward(node, success):
    reward = 0
    if success:
        reward += 5
    else:
        reward -= 10

    reward += node.throughput / 100
    reward -= node.latency / 200

    return reward


def voting(nodes, leader_id):
    votes = 0
    for node in nodes:
        if node.node_id != leader_id:
            if random.random() < 0.9:
                votes += 1
    return votes >= 2


# Simulated Actions
def update_ehr():
    print("EHR record updated successfully.")


def chameleon_hash():
    print("Radaction was successful")


# -----------------------------
# MAIN PROGRAM
# -----------------------------
def main():

    nodes = [HospitalNode(i) for i in range(4)]
    agent = RLAgent(state_size=16, action_size=4)

    while True:

        print("\n==============================")
        print("AI Leader Election")
        print("==============================")
        print("1. Update value in EHR")
        print("2. Redaction")
        print("3. Exit")

        choice = input("Choose option: ")

        if choice == "3":
            print("Exiting program...")
            break

        # Update node metrics
        for node in nodes:
            node.update_metrics()

        print("\n Current Hospital Metrics:")
        for node in nodes:
            print(f"Hospital {node.node_id} | "
                  f"Throughput: {node.throughput:.2f} | "
                  f"Latency: {node.latency:.2f} | "
                  f"CPU: {node.cpu:.2f}")

        state = get_state(nodes)

        # AI selects leader
        leader_id = agent.select_action(state)
        leader = nodes[leader_id]

        print(f"\nSelected Leader: Hospital {leader_id}")

        success = leader.perform_task()

        if success:
            print("Leader verification SUCCESS")
        else:
            print("Leader verification FAILED")

        if voting(nodes, leader_id):
            print("Voting PASSED")

            if choice == "1":
                update_ehr()
            elif choice == "2":
                chameleon_hash()

        else:
            print("⚠ Voting FAILED")

        reward = compute_reward(leader, success)
        print(f"Reward received: {reward:.2f}")

        # Next state
        for node in nodes:
            node.update_metrics()

        next_state = get_state(nodes)

        agent.train(state, leader_id, reward, next_state)


if __name__ == "__main__":
    main()




