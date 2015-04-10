with import <nixpkgs> {};
with pkgs.pythonPackages;

buildPythonPackage {

  name = "heavy-sync-0.1";

  src = ./.;

  propagatedBuildInputs = [
    boto gcs-oauth2-boto-plugin
    sqlite3 # For SQLite 3 support in Python
  ];

  meta = with stdenv.lib; {
    description = "Synchronize huge cloud buckets with ease";
    homepage = "https://github.com/zalora/heavy-sync";
    license = licenses.mpl20;
  };
}
