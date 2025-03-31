{pkgs}: {
  deps = [
    pkgs.wkhtmltopdf
    pkgs.pandoc
    pkgs.postgresql
    pkgs.openssl
  ];
}
