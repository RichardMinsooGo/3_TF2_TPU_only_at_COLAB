import tensorflow as tf
import gym
import numpy as np
import random
from collections import deque
import dqn
from typing import List
import time
import pylab
import sys
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from tensorflow.python.framework import ops
ops.reset_default_graph()

env_name = "Acrobot-v1"
env = gym.make(env_name)
# env.seed(1)     # reproducible, general Policy gradient has high variance
# np.random.seed(123)
# tf.set_random_seed(456)  # reproducible
env = env.unwrapped

state_size = env.observation_space.shape[0]
action_size = env.action_space.n

file_name =  sys.argv[0][:-3]

model_path = "save_model/" + file_name
graph_path = "save_graph/" + file_name

# Make folder for save data
if not os.path.exists(model_path):
    os.makedirs(model_path)
if not os.path.exists(graph_path):
    os.makedirs(graph_path)

learning_rate = 0.001
discount_factor = 0.99
        
epsilon_max = 1.0
epsilon_min = 0.0001
epsilon_decay = 0.0001

hidden1 = 256
target_update_cycle = 200

memory = []
size_replay_memory = 50000
batch_size = 64


def Copy_Weights(*, dest_scope_name: str, src_scope_name: str) -> List[tf.Operation]:
    op_holder = []

    src_vars = tf.get_collection(
        tf.GraphKeys.TRAINABLE_VARIABLES, scope=src_scope_name)
    dest_vars = tf.get_collection(
        tf.GraphKeys.TRAINABLE_VARIABLES, scope=dest_scope_name)

    for src_var, dest_var in zip(src_vars, dest_vars):
        op_holder.append(dest_var.assign(src_var.value()))

    return op_holder
                 
def train_model(agent: dqn.DQN, target_agent: dqn.DQN, minibatch: list) -> float:
    states      = np.vstack([batch[0] for batch in minibatch])
    actions     = np.array( [batch[1] for batch in minibatch])
    rewards     = np.array( [batch[2] for batch in minibatch])
    next_states = np.vstack([batch[3] for batch in minibatch])
    dones       = np.array( [batch[4] for batch in minibatch])

    X_batch = states
    q_value = agent.predict(states)
    q_value_next = agent.predict(next_states)
    tgt_q_value_next = target_agent.predict(next_states)
    
    for i in range(batch_size):
        if dones[i]:
            q_value[i][actions[i]] = rewards[i]
        else:
            a = np.argmax(tgt_q_value_next[i])
            q_value[i][actions[i]] = rewards[i] + discount_factor * q_value_next[i][a]        

    return agent.update(X_batch, q_value)

def main():

    memory = deque(maxlen=size_replay_memory)
    progress = " "

    with tf.Session() as sess:
        agent = dqn.DQN(sess, state_size, action_size, name="main")
        target_agent = dqn.DQN(sess, state_size, action_size, name="target")
        
        init = tf.global_variables_initializer()
        saver = tf.train.Saver()
        sess.run(init)
        
        copy_ops = Copy_Weights(dest_scope_name="target",
                                    src_scope_name="main")
        sess.run(copy_ops)
        
        avg_score = 10000
        episode = 0
        episodes, scores = [], []
        epsilon = epsilon_max
        start_time = time.time()

        while time.time() - start_time < 10 * 60 and avg_score > 90:
            
            state = env.reset()
            score = 0
            done = False
            ep_step = 0
            
            while not done and ep_step < 10000 :

                if len(memory) < size_replay_memory:
                    progress = "Exploration"            
                else:
                    progress = "Training"

                #env.render()
                ep_step += 1
                
                if epsilon > np.random.rand(1):
                    action = env.action_space.sample()
                else:
                    action = np.argmax(agent.predict(state))

                next_state, reward, done, _ = env.step(action)
                memory.append((state, action, reward, next_state, done))

                if len(memory) > size_replay_memory:
                    memory.popleft()
                
                if progress == "Training":
                    minibatch = random.sample(memory, batch_size)
                    LossValue,_ = train_model(agent,target_agent, minibatch)
                    
                    if epsilon > epsilon_min:
                        epsilon -= epsilon_decay
                    else:
                        epsilon = epsilon_min
                        
                if done or ep_step % target_update_cycle == 0:
                    sess.run(copy_ops)
                        
                state = next_state
                score = ep_step

                if done or ep_step == 10000:
                    if progress == "Training":
                        episode += 1
                        scores.append(score)
                        episodes.append(episode)
                        avg_score = np.mean(scores[-min(30, len(scores)):])

                    print("episode {:>5d} / score:{:>5d} / recent 30 game avg:{:>5.1f} / epsilon :{:>1.5f}"
                              .format(episode, score, avg_score, epsilon))            
                    break

        save_path = saver.save(sess, model_path + "/model.ckpt")
        print("\n Model saved in file: %s" % save_path)

        pylab.plot(episodes, scores, 'b')
        pylab.savefig(graph_path + "/cartpole_NIPS2013.png")

        e = int(time.time() - start_time)
        print(' Elasped time :{:02d}:{:02d}:{:02d}'.format(e // 3600, (e % 3600 // 60), e % 60))

    # Replay the result
        episode = 0
        scores = []
        while episode < 20:
            
            state = env.reset()
            done = False
            ep_step = 0
            
            while not done and ep_step < 1000:
                env.render()
                ep_step += 1
                q_value = agent.predict(state)
                action = np.argmax(q_value)
                next_state, reward, done, _ = env.step(action)
                state = next_state
                score = ep_step
                
                if done or ep_step == 1000:
                    episode += 1
                    scores.append(score)
                    print("episode : {:>5d} / reward : {:>5d} / avg reward : {:>5.2f}".format(episode, score, np.mean(scores)))

if __name__ == "__main__":
    main()
