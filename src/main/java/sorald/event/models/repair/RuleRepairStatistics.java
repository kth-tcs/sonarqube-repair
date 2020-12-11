package sorald.event.models.repair;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import sorald.event.StatisticsCollector;
import sorald.event.models.RepairEvent;
import sorald.event.models.WarningLocation;
import sorald.event.models.miner.MinedViolationEvent;
import sorald.sonar.Checks;

/** Repair statistics for a single rule. */
public class RuleRepairStatistics {
    private final String ruleKey;
    private final String ruleName;
    private final List<MinedViolationEvent> allWarnings;
    private final List<WarningLocation> performedRepairsLocations;
    private final List<WarningLocation> crashedRepairsLocations;

    public RuleRepairStatistics(
            String ruleKey,
            String ruleName,
            List<MinedViolationEvent> allWarnings,
            List<RepairEvent> repairedWarnings,
            List<RepairEvent> failedRepairs,
            Path projectPath) {
        this.ruleKey = ruleKey;
        this.ruleName = ruleName;
        this.allWarnings = new ArrayList<>(allWarnings);

        this.performedRepairsLocations = toWarningLocations(repairedWarnings, projectPath);
        this.crashedRepairsLocations = toWarningLocations(failedRepairs, projectPath);
    }

    private static List<WarningLocation> toWarningLocations(
            List<RepairEvent> repairEvents, Path projectPath) {
        return repairEvents.stream()
                .map(
                        repairEvent ->
                                new WarningLocation(repairEvent.getRuleViolation(), projectPath))
                .collect(Collectors.toList());
    }

    public String getRuleKey() {
        return ruleKey;
    }

    public String getRuleName() {
        return ruleName;
    }

    public List<WarningLocation> getPerformedRepairsLocations() {
        return Collections.unmodifiableList(performedRepairsLocations);
    }

    public List<WarningLocation> getCrashedRepairsLocations() {
        return Collections.unmodifiableList(crashedRepairsLocations);
    }

    public int getNbFoundWarnings() {
        return allWarnings.size();
    }

    public int getNbPerformedRepairs() {
        return performedRepairsLocations.size();
    }

    public int getNbCrashedRepairs() {
        return crashedRepairsLocations.size();
    }

    public static List<RuleRepairStatistics> createRepairStatsList(
            StatisticsCollector statsCollector, Path projectPath) {
        Map<String, List<RepairEvent>> keyToRepair = statsCollector.performedRepairs();
        Map<String, List<RepairEvent>> keyToFailure = statsCollector.crashedRepairs();
        Map<String, List<MinedViolationEvent>> keyToWarnings = statsCollector.minedWarnings();

        Set<String> distinctKeys = new HashSet<>(keyToRepair.keySet());
        distinctKeys.addAll(keyToFailure.keySet());

        return distinctKeys.stream()
                .map(
                        key -> {
                            List<RepairEvent> repairs = keyToRepair.getOrDefault(key, List.of());
                            List<RepairEvent> failures = keyToFailure.getOrDefault(key, List.of());
                            List<MinedViolationEvent> allWarnings =
                                    keyToWarnings.getOrDefault(key, List.of());
                            String checkName = Checks.getCheck(key).getSimpleName();
                            return new RuleRepairStatistics(
                                    key,
                                    checkName.replace("Check", ""),
                                    allWarnings,
                                    repairs,
                                    failures,
                                    projectPath);
                        })
                .collect(Collectors.toList());
    }
}