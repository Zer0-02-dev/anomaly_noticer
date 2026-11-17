from setuptools import setup

setup(
    name='anomaly_noticer',
    version='1.0.0',
    description='ML-based spam classifier for imageboard posts',
    author='Zer0',
    package_dir={
        'anomaly_noticer': 'python',
        'anomaly_noticer/data': 'data',
        },
    packages=['anomaly_noticer', 'anomaly_noticer/data'],
    package_data={
        'anomaly_noticer': ['model.joblib'],
    },
    include_package_data=True,
    install_requires=[
        'scikit-learn>=1.0',
        'scipy>=1.7',
        'numpy>=1.20',
        'joblib>=1.0',
    ],
    python_requires='>=3.8',
    zip_safe=False,
)
