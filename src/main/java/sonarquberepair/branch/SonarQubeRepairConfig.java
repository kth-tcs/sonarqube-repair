package sonarquberepair.branch;

import java.util.List;
import java.util.ArrayList;

public class SonarQubeRepairConfig {
	private static SonarQubeRepairConfig config;
	private final List<Integer> ruleNumbers = new ArrayList<Integer>();
	private String projectKey;
	private RepairMode repairMode;
	private String repairPath;

	private SonarQubeRepairConfig() {}

	public static SonarQubeRepairConfig getInstance() {
		if (config == null) {
			config = new SonarQubeRepairConfig();
		}
		return config;
	}

	public void setProjectKey(String projectKey) {
		this.projectKey = projectKey;
	}

	public String getProjectKey() {
		return this.projectKey;
	}


	public void addRuleNumbers(int ruleNumber) {
		this.ruleNumbers.add(ruleNumber);
	}

	public List<Integer> getRuleNumbers() {
		return this.ruleNumbers;
	}

	public void setRepairMode(RepairMode repairMode) {
		this.repairMode = repairMode;
	}

	public RepairMode getRepairMode() {
		return repairMode;
	}

	public void setRepairPath(String repairPath) {
		this.repairPath = repairPath;
	}

	public String getRepairPath() {
		return this.repairPath;
	}
}