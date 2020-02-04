import typing
import itertools
import numpy as np
import gym
from gym.spaces import Box, Discrete, MultiDiscrete, Tuple

from regym.environments.task import Task, EnvType


def parse_gym_environment(env: gym.Env, env_type: EnvType) -> Task:
    '''
    Generates a regym.environments.Task by extracting information from the
    already built :param: env.

    This function makes the following Assumptions from :param: env:
        - Observation / Action space (it's geometry, dimensionality) are identical for all agents

    :param env: Environment following OpenAI Gym interface
    :param env_type: Determines whether the parameter is (single/multi)-agent
                     and how are the environment processes these actions
                     (i.e all actions simultaneously, or sequentially)
    :returns: Task created from :param: env named :param: name
    '''
    name = env.spec.id
    action_dims, action_type = get_action_dimensions_and_type(env)
    observation_dims, observation_type = get_observation_dimensions_and_type(env)
    state_space_size = env.state_space_size if hasattr(env, 'state_space_size') else None
    action_space_size = env.action_space_size if hasattr(env, 'action_space_size') else None
    hash_function = env.hash_state if hasattr(env, 'hash_state') else None
    if env_type == EnvType.SINGLE_AGENT: num_agents = 1
    else: num_agents = len(env.observation_space.spaces)

    check_env_compatibility_with_env_type(env, env_type)

    return Task(name, env, env_type, state_space_size, action_space_size,
                observation_dims, observation_type, action_dims, action_type,
                num_agents, hash_function)


# TODO: box environments are considered continuous.
# Update so that if (space.dtype == an int type), then the space is considered discrete
def get_observation_dimensions_and_type(env: gym.Env) -> typing.Tuple[int, str]:
    def parse_dimension_space(space):
        if isinstance(space, Discrete): return 1, 'Discrete' # One neuron is enough to take any Discrete space
        elif isinstance(space, Box): return int(np.prod(space.shape)), 'Continuous'
        elif isinstance(space, Tuple): return sum([parse_dimension_space(s)[0] for s in space.spaces]), parse_dimension_space(space.spaces[0])[1]
        # Below space refers to OneHotEncoding space from 'https://github.com/Danielhp95/gym-rock-paper-scissors'
        elif hasattr(space, 'size'): return space.size, 'Discrete'
        raise ValueError('Unknown observation space: {}'.format(space))

    # ASSUMPTION: Multi agent environment. Symmetrical observation space
    if hasattr(env.observation_space, 'spaces'): return parse_dimension_space(env.observation_space.spaces[0])
    else: return parse_dimension_space(env.observation_space) # Single agent environment


def get_action_dimensions_and_type(env) -> typing.Tuple[int, str]:
    def parse_dimension_space(space):
        if isinstance(space, Discrete): return space.n, 'Discrete'
        elif isinstance(space, MultiDiscrete): return compute_multidiscrete_space_size(space.nvec), 'Discrete'
        elif isinstance(space, Box): return space.shape[0], 'Continuous'
        else: raise ValueError('Unknown action space: {}'.format(space))

    if hasattr(env.action_space, 'spaces'): return parse_dimension_space(env.action_space.spaces[0]) # Multi agent environment
    else: return parse_dimension_space(env.action_space) # Single agent environment


def compute_multidiscrete_space_size(flattened_multidiscrete_space) -> int:
    """
    Computes size of the combinatorial space generated by :param: flattened_multidiscrete_space

    :param multidiscrete_action_space: gym.spaces.MultiDiscrete space
    :returns: Size of 'flattened' :param: flattened_multidiscrete_space
    """
    possible_vals = [range(_num) for _num in flattened_multidiscrete_space]
    return len([list(_action) for _action in itertools.product(*possible_vals)])


def check_env_compatibility_with_env_type(env: gym.Env, env_type: EnvType):
    # Environment is multiagent but it has been declared single agent
    if hasattr(env.observation_space, 'spaces') \
            and env_type == EnvType.SINGLE_AGENT:
                error_msg = \
f'''
The environment ({env.spec.id}) appears to be multiagent (it has multiple observation spaces).
But parameter \'env_type\' was set to EnvType.SINGLE_AGENT (default value).
Suggestion: Change to a multiagent EnvType.
'''
                raise ValueError(error_msg)
    # Environment is single agent but it has been declared multiagent
    if not hasattr(env.observation_space, 'spaces') \
            and env_type != EnvType.SINGLE_AGENT:
                error_msg = \
f'''
The environment ({env.spec.id}) appears to be single agent
But parameter \'env_type\' was set to {env_type}
Suggestion: Change to a EnvType.SINGLE_AGENT
'''
                raise ValueError(error_msg)
