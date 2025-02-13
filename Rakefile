begin
  require 'github_changelog_generator/task'
rescue LoadError
  # github_changelog_generator is an optional group
else
  GitHubChangelogGenerator::RakeTask.new :changelog do |config|
    version = File.readlines('pyproject.toml').find{ |l| l.match(/version/) }.split(' ').last.gsub('"', '')
    config.future_release = "v#{version}" if /^\d+\.\d+.\d+$/.match?(version)
    config.header = "# Changelog\n\nAll notable changes to this project will be documented in this file."
    config.exclude_labels = %w[duplicate question invalid wontfix wont-fix skip-changelog github_actions]
    config.user = 'voxpupuli'
    config.project = 'puppetboard'
  end
end
