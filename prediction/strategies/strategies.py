"""Init strategies to be used for running jobs."""
import yaml
import os
import numpy as np
from sklearn.model_selection import ShuffleSplit, GridSearchCV, \
    RandomizedSearchCV, KFold
from sklearn.experimental import enable_hist_gradient_boosting
from sklearn.ensemble import HistGradientBoostingClassifier, \
    HistGradientBoostingRegressor
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import SimpleImputer, IterativeImputer
from copy import deepcopy

from scipy.stats import uniform
from sklearn.utils.fixes import loguniform

from .strategy import Strategy


RS = 42
strategies = list()

# Load some params from custom file
filepath = 'custom/strategy_params.yml'
if os.path.exists(filepath):
    with open(filepath, 'r') as file:
        params = yaml.safe_load(file)
else:
    params = dict()

# Load or defaults
n_outer_splits = params.get('n_outer_splits', 2)
n_inner_splits = params.get('n_inner_splits', 2)
n_jobs = params.get('n_jobs', 1)
n_iter = params.get('n_iter', 1)
n_repeats = params.get('n_repeats', 1)
compute_importance = params.get('compute_importance', False)
learning_curve = params.get('learning_curve', False)


# A strategy to run a classification
strategies.append(Strategy(
    name='Classification',
    estimator=HistGradientBoostingClassifier(),
    inner_cv=ShuffleSplit(n_splits=n_inner_splits, train_size=0.8, random_state=RS),
    # param_space={
    #     'learning_rate': [0.01],#np.linspace(0.01, 0.15, 3),
    #     'max_iter': [100]#[100, 500, 1000]
    # },
    # search=GridSearchCV,
    param_space={
        'learning_rate': uniform(1e-5, 1),
        'max_iter': range(10, 500)
    },
    search=RandomizedSearchCV,
    search_params={
        'scoring': 'recall',
        'verbose': 2,
        'n_jobs': n_jobs,
        'return_train_score': True,
        'n_iter': n_iter
    },
    outer_cv=KFold(n_splits=n_outer_splits, shuffle=True, random_state=RS),
    compute_importance=compute_importance,
    importance_params={
        'n_jobs': n_jobs,
        'n_repeats': n_repeats,
    },
    learning_curve=learning_curve,
    learning_curve_params={
        'scoring': 'roc_auc_ovr_weighted',
        'n_jobs': n_jobs
    }
))

# A strategy to run a regression
strategies.append(Strategy(
    name='Regression',
    estimator=HistGradientBoostingRegressor(loss='least_absolute_deviation'),
    inner_cv=ShuffleSplit(n_splits=n_inner_splits, train_size=0.8, random_state=RS),
    # param_space={
    #     'learning_rate': np.array([0.1]),#np.linspace(0.001, 0.1, 5),#[0.1, 0.15, 0.2, 0.25],
    #     'max_depth': [3]#[3, 6, 8]
    # },
    # search=GridSearchCV,
    param_space={
        'learning_rate': uniform(1e-5, 1),
        'max_depth': range(3, 11)
    },
    search=RandomizedSearchCV,
    search_params={
        'scoring': ['r2', 'neg_mean_absolute_error'],
        'refit': 'r2',
        'verbose': 2,
        'return_train_score': True,
        'n_iter': n_iter
    },
    outer_cv=KFold(n_splits=n_outer_splits, shuffle=True, random_state=RS),
    compute_importance=compute_importance,
    importance_params={
        'n_jobs': n_jobs,
        'n_repeats': n_repeats,
    },
    learning_curve=learning_curve,
    learning_curve_params={
        'scoring': 'r2',
        'n_jobs': n_jobs
    }
))


# Add imputation to the previous strategies
imputers = {
    'Mean': SimpleImputer(strategy='mean'),
    'Mean+mask': SimpleImputer(strategy='mean', add_indicator=True),
    'Med': SimpleImputer(strategy='median'),
    'Med+mask': SimpleImputer(strategy='median', add_indicator=True),
    'Iterative': IterativeImputer(),
    'Iterative+mask': IterativeImputer(add_indicator=True),
}

# Add imputed versions of the previosu strategies
imputed_strategies = list()

for imputer_name, imputer in imputers.items():
    for strategy in strategies:
        strategy = deepcopy(strategy)
        strategy.imputer = imputer
        strategy.name = f'{strategy.name}_imputed_{imputer_name}'
        imputed_strategies.append(strategy)

strategies = strategies + imputed_strategies
strategies = {strategy.name: strategy for strategy in strategies}

