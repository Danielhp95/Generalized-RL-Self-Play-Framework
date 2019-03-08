import os
import sys
sys.path.append(os.path.abspath('..'))

import util
from training_schemes import EmptySelfPlay, NaiveSelfPlay, HalfHistorySelfPlay, FullHistorySelfPlay

from rl_algorithms import AgentHook
from environments import ParallelEnv, EnvironmentCreationFunction, ParallelEnvironmentCreationFunction

from training_process import create_training_processes
from match_making import match_making_process
from confusion_matrix_populate_process import confusion_matrix_process

from torch.multiprocessing import Process, JoinableQueue

import roboschool
import gym
import gym_rock_paper_scissors

from collections import namedtuple
TrainingJob = namedtuple('TrainingJob', 'training_scheme agent name')


def enumerate_training_jobs(training_schemes, algorithms, env_name):
    a = [TrainingJob(training_scheme, AgentHook(algorithm.clone(training=True)), f'{training_scheme.name}-{algorithm.name}')
        for training_scheme in training_schemes
        for algorithm in algorithms]
    b = [EnvironmentCreationFunction(env_name) if not('nbr_actor' in agent.algorithm.kwargs) else ParallelEnvironmentCreationFunction(env_name, agent.algorithm.kwargs['nbr_actor'])
        for training_scheme in training_schemes
        for agent in algorithms]
    c = EnvironmentCreationFunction(env_name)
    return a,b,c

def preprocess_fixed_agents(existing_fixed_agents, checkpoint_at_iterations, env_name):
    initial_fixed_agents_to_benchmark = [[iteration, EmptySelfPlay, AgentHook(agent)]
                                         for agent in existing_fixed_agents
                                         for iteration in checkpoint_at_iterations]
    fixed_agents_for_confusion, _, _ = enumerate_training_jobs([EmptySelfPlay], existing_fixed_agents, env_name) # TODO GET RID OF THIS
    return initial_fixed_agents_to_benchmark, fixed_agents_for_confusion


def create_all_initial_processes(training_jobs, training_environments, benchmarking_environment, checkpoint_at_iterations,
                                 agent_queue, matrix_queue, benchmarking_episodes,
                                 fixed_agents_for_confusion, results_path):

    # TODO Set magic number to number of available cores - (training processes - matchmaking - confusion matrix)
    benchmark_process_number_workers = 4
    benchmark_process_pool = None # ProcessPoolExecutor(max_workers=benchmark_process_number_workers)

    training_processes = create_training_processes(training_jobs, training_environments,
                                                   checkpoint_at_iterations=checkpoint_at_iterations,
                                                   agent_queue=agent_queue, results_path=results_path)

    expected_number_of_agents = (len(training_jobs) + len(fixed_agents_for_confusion)) * len(checkpoint_at_iterations)
    mm_process = Process(target=match_making_process,
                         args=(expected_number_of_agents, benchmarking_episodes, benchmarking_environment,
                               agent_queue, matrix_queue, benchmark_process_pool))

    cfm_process = Process(target=confusion_matrix_process,
                          args=(training_jobs + fixed_agents_for_confusion, checkpoint_at_iterations,
                                matrix_queue, results_path))
    return (training_processes, mm_process, cfm_process)



def run_processes(training_processes, mm_process, cfm_process):
    [p.start() for p in training_processes]
    mm_process.start()
    cfm_process.start()

    [p.join() for p in training_processes]
    mm_process.join()
    cfm_process.join()


def run_experiment(experiment_id, experiment_directory, run_id, experiment_config, agents_config):
    results_path = f'{experiment_directory}/run-{run_id}'
    if not os.path.exists(results_path):
        os.mkdir(results_path)
    base_path = results_path

    createNewEnvironment  = EnvironmentCreationFunction(experiment_config['environment'])
    env = createNewEnvironment()

    checkpoint_at_iterations = [int(i) for i in experiment_config['checkpoint_at_iterations']]
    benchmarking_episodes    = int(experiment_config['benchmarking_episodes'])

    training_schemes  = util.experiment_parsing.initialize_training_schemes(experiment_config['self_play_training_schemes'])
    algorithms        = util.experiment_parsing.initialize_algorithms(env, agents_config)
    fixed_agents      = util.experiment_parsing.initialize_fixed_agents(experiment_config['fixed_agents'])

    training_jobs, training_environments, benchmarking_environment = enumerate_training_jobs(training_schemes, algorithms, experiment_config['environment'])

    (initial_fixed_agents_to_benchmark, fixed_agents_for_confusion) = preprocess_fixed_agents(fixed_agents, checkpoint_at_iterations, experiment_config['environment'])
    agent_queue, matrix_queue = JoinableQueue(), JoinableQueue()

    for fixed_agent in initial_fixed_agents_to_benchmark: agent_queue.put(fixed_agent)

    (training_processes,
     mm_process,
     cfm_process) = create_all_initial_processes(training_jobs, training_environments, benchmarking_environment, checkpoint_at_iterations,
                                                 agent_queue, matrix_queue, benchmarking_episodes,
                                                 fixed_agents_for_confusion, results_path)

    run_processes(training_processes, mm_process, cfm_process)
