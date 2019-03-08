import os
import sys
sys.path.append(os.path.abspath('../../'))

from test_fixtures import ddpg_config_dict, RoboSumoenv, RoboSumoTask

from rl_algorithms.agents import build_DDPG_Agent
from rl_algorithms import AgentHook


def test_ppo_can_take_actions(RoboSumoenv, RoboSumoTask, ddpg_config_dict):
    agent = build_DDPG_Agent(RoboSumoTask, ppo_config_dict)
    RoboSumoenv.reset()
    number_of_actions = 30
    for i in range(number_of_actions):
        # asumming that first observation corresponds to observation space of this agent
        random_observation = RoboSumoenv.observation_space.sample()[0]
        a = agent.take_action(random_observation)
        observation, rewards, done, info = RoboSumoenv.step([a, a])
        # TODO technical debt
        # assert RoboSumoenv.observation_space.contains([a, a])
        # assert RoboSumoenv.action_space.contains([a, a])


def test_learns_to_beat_rock_in_RoboSumo(RoboSumoTask, ddpg_config_dict):
    '''
    Test used to make sure that agent is 'learning' by learning a best response
    against an agent that only plays rock in rock paper scissors.
    i.e from random, learns to play only (or mostly) paper
    '''
    load = False 
    
    from RoboSumo_test import learns_against_fixed_opponent_RoboSumo

    if load:
        agent = AgentHook.load(load_path='/tmp/test_ddpg_roboschoolsumo.agent')
    else:
        agent = build_DDPG_Agent(RoboSumoTask, ppo_config_dict)
    assert agent.training
    opponent = build_DDPG_Agent(RoboSumoTask, ppo_config_dict)
    opponent.training = False
    learns_against_fixed_opponent_RoboSumo(agent, fixed_opponent=opponent,
                                      total_episodes=1000, training_percentage=0.9,
                                      reward_threshold_percentage=0.25)
    agent_hook = AgentHook(agent, save_path='/tmp/test_ppo_roboschoolsumo.agent')