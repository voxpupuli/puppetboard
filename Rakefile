begin
  require 'github_changelog_generator/task'
rescue LoadError
  # github_changelog_generator is an optional group
else
  GitHubChangelogGenerator::RakeTask.new :changelog do |config|
    config.future_release = `git rev-parse --abbrev-ref HEAD`.strip.split('-', 2).last
    config.header = "# Changelog\n\nAll notable changes to this project will be documented in this file."
    config.exclude_labels = %w[duplicate question invalid wontfix wont-fix skip-changelog github_actions]
    config.user = 'voxpupuli'
    config.project = 'puppetboard'
  end
end
