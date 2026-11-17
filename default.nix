{ pkgs ? import <nixpkgs> {} }:

with pkgs;

python3Packages.buildPythonPackage rec {
  pname = "anomaly_noticer";
  version = "1.0.0";
  format = "setuptools";

  # Filter the source to only include the files we want to distribute.
  src = lib.cleanSourceWith {
    src = ./.;
    filter = path: type:
      let
        relPath = lib.removePrefix (toString ./. + "/") (toString path);
      in
      # Always include directories (needed for traversal)
      type == "directory" ||
      # Top-level files
      relPath == "setup.py" ||
      relPath == "default.nix" ||
      relPath == "MANIFEST.in" ||
      relPath == ".gitignore" ||
      # Package source (only these three .py files)
      relPath == "python/__init__.py" ||
      relPath == "python/canon.py" ||
      relPath == "python/ml_classifier.py" ||
      # The trained model
      relPath == "data/model.joblib";
  };

  propagatedBuildInputs = with python3Packages; [
    scikit-learn
    scipy
    numpy
    joblib
  ];

  # # Copy model.joblib into the package directory so ml_classifier can find it
  # preInstall = ''
  #   mkdir -p $out/${python3.sitePackages}/anomaly_noticer
  #   cp data/model.joblib $out/${python3.sitePackages}/anomaly_noticer/
  # '';

  meta = with lib; {
    description = "ML-based spam classifier for imageboard posts";
    license = licenses.mit;
    platforms = platforms.all;
  };
}
