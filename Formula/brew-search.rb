class BrewSearch < Formula
  include Language::Python::Virtualenv

  desc "Fast offline-first search of Homebrew formulae, casks, taps, and installed packages"
  homepage "https://github.com/steward/brew-search"
  url "https://files.pythonhosted.org/packages/source/b/brew-search/brew_search-0.2.0.tar.gz"
  sha256 "PLACEHOLDER"
  license "MIT"

  depends_on "python@3.12"

  resource "sqlite-utils" do
    url "https://files.pythonhosted.org/packages/source/s/sqlite-utils/sqlite_utils-3.38.tar.gz"
    sha256 "PLACEHOLDER"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "brew-search", shell_output("#{bin}/brew-search --help")
  end
end
