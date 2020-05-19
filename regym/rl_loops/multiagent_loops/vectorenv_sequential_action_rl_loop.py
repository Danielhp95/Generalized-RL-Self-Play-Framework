from typing import List, Tuple, Any, Dict
from copy import deepcopy

import numpy as np
import gym

import regym
from regym.rl_algorithms.agents import Agent
from regym.environments.tasks import RegymAsyncVectorEnv

from regym.rl_loops.utils import update_parallel_sequential_trajectories, update_finished_trajectories


def async_run_episode(env: RegymAsyncVectorEnv, agent_vector: List, training: bool,
                      num_episodes: int) \
                      -> List[List[Tuple[Any, Any, Any, Any, bool]]]:
    '''
    TODO: document, refactor
    '''
    ongoing_trajectories: List[List[Tuple[Any, Any, Any, Any, bool]]]
    ongoing_trajectories = [[] for _ in range(env.num_envs)]
    finished_trajectories = []

    obs = env.reset()
    current_players: List[int] = [0] * env.num_envs
    legal_actions: List[List] = [None] * env.num_envs # Revise
    num_agents = len(agent_vector)
    while len(finished_trajectories) < num_episodes:

        # Take action
        action_vector = multienv_choose_action(
                agent_vector, env, obs, current_players, legal_actions)

        # Environment step
        succ_obs, rewards, dones, infos = env.step(action_vector)

        # Update trajectories:
        update_parallel_sequential_trajectories(ongoing_trajectories, current_players,
                action_vector, obs, rewards, succ_obs, dones)
        done_envs = update_finished_trajectories(ongoing_trajectories,
                                                 finished_trajectories, dones)

        # Update agents
        if training: propagate_experiences(agent_vector, ongoing_trajectories)

        # Update observation
        obs = succ_obs

        # Update current players and legal actions
        legal_actions = [info.get('legal_actions', None) for info in infos]
        current_players = [info.get('current_player',
                                    (current_players[e_i] + 1) % num_agents)
                           for e_i, info in enumerate(infos)]

        # Deal with episode termination
        if len(done_envs) > 0 :
            # Reset players and trajectories
            if training:
                propagate_last_experience(agent_vector,
                                          finished_trajectories[-(i + 1)])
            for i, e_i in enumerate(done_envs):
                current_players[e_i] = 0
                ongoing_trajectories[e_i] = []

    return finished_trajectories


def multienv_choose_action(agent_vector, env: RegymAsyncVectorEnv, obs,
                            current_players, legal_actions):
    action_vector = [None] * env.num_envs
    # Find indices of which envs each player should play, on a dict
    agent_signals = extract_signals_for_acting_agents(
            agent_vector, env, obs, current_players, legal_actions)

    for a_i, signals in agent_signals.items():
        a = agent_vector[a_i]
        if not a.requires_environment_model:
            partial_action_vector = a.model_free_take_action(
                    signals['obs'], legal_actions=signals['legal_actions'],
                    multi_action=True)
        else:
            envs = env.get_envs()
            relevant_envs = {e_i: envs[e_i] for e_i in signals['env_ids']}
            observations = {e_i: o for e_i, o in zip(signals['env_ids'], signals['obs'])}
            partial_action_vector = a.model_based_take_action(
                    relevant_envs, observations, a_i, multi_action=True)
        # fill action_vector
        for env_id, action in zip(signals['env_ids'], partial_action_vector):
            assert action_vector[env_id] is None
            action_vector[env_id] = action
    return action_vector


def propagate_experiences(agent_vector, trajectories):
    '''
    TODO
    '''
    agents_to_update_per_env = {i: len(t) % len(agent_vector)
                                for i, t in enumerate(trajectories)
                                if len(t) >= len(agent_vector)}
    if agents_to_update_per_env == {}:
        # No agents to update
        return

    agents_to_update = set(agents_to_update_per_env.values())
    environment_per_agents = {a_i: [env_i
                                    for env_i, a_j in agents_to_update_per_env.items()
                                    if a_i == a_j]
                              for a_i in agents_to_update}

    agent_experiences = collect_agent_experiences_from_trajectories(
            agents_to_update, agents_to_update_per_env, trajectories, agent_vector)

    propagate_batched_experiences(agent_experiences, agent_vector, environment_per_agents)


def propagate_batched_experiences(agent_experiences, agent_vector, environment_per_agents):
    for a_i, experiences in agent_experiences.items():
        if agent_vector[a_i].training:
            agent_vector[a_i].handle_multiple_experiences(
                    experiences, environment_per_agents[a_i])


def collect_agent_experiences_from_trajectories(agents_to_update, agents_to_update_per_env, trajectories, agent_vector):
    agent_experiences = {a_i: [] for a_i in agents_to_update}

    for env_i, target_agent in agents_to_update_per_env.items():
        experience = extract_latest_experience(target_agent,
                           trajectories[env_i], agent_vector)
        agent_experiences[target_agent] += [experience]
    return agent_experiences


def extract_latest_experience(agent_id: int, trajectory: List, agent_vector: List):
    '''
    ASSUMPTION:
        - every non-terminal observation corresponds to
          the an information set unique for the player whose turn it is.
          This means that each "experience" is from which an RL agent will learn
          (o, a, r, o') is fragmented throughout the trajectory. This function
          "stiches together" the right environmental signals, ensuring that
          each agent only has access to information from their own information sets.

    :param agent_id: Index of agent which will receive a new experience
    :param trajectory: Current episode trajectory
    :param agent_vector: List of agents acting in current environment
    '''
    o, a = get_last_observation_and_action_for_agent(agent_id,
                                                     trajectory,
                                                     len(agent_vector))
    (_, _, reward, succ_observation, done) = trajectory[-1]
    return (o, a, reward[agent_id], succ_observation[agent_id], done)


def extract_signals_for_acting_agents(agent_vector, env, obs,
                                      current_players, legal_actions) \
                                              -> Dict[int, Dict[str, List]]:
    agent_signals: Dict[int, Dict[str, List]] = dict()

    # Extract signals for each acting agent
    for e_i, cp in enumerate(current_players):
        if cp not in agent_signals:
            agent_signals[cp] = dict()
            agent_signals[cp]['obs'] = []
            agent_signals[cp]['legal_actions'] = []
            agent_signals[cp]['env_ids'] = []
        agent_signals[cp]['obs'] += [obs[cp][e_i]]
        agent_signals[cp]['legal_actions'] += [legal_actions[e_i]]
        agent_signals[cp]['env_ids'] += [e_i]
    return agent_signals


def get_last_observation_and_action_for_agent(target_agent_id: int,
                                              trajectory: List, num_agents: int) -> Tuple:
    '''
    # TODO: assume games where turns are taken in cyclic fashion.

    Obtains the last observation and action for agent :param: target_agent_id
    from the :param: trajectory.

    :param target_agent_id: Index of agent whose last observation / action
                            we are searching for
    :param trajectory: Sequence of (o_i,a_i,r_i,o'_{i+1}) for all players i.
    :param num_agents: Number of agents acting in the current environment
    :returns: The last observation (information state) and action taken
              at such observation by player :param: target_agent_id.
    '''
    # Offsets are negative, exploiting Python's backwards index lookup
    previous_timestep = trajectory[-num_agents]
    last_observation = previous_timestep[0][target_agent_id]
    last_action = previous_timestep[1]
    return last_observation, last_action