package sorald;

import java.io.File;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.util.List;
import sorald.processor.SoraldAbstractProcessor;
import spoon.Launcher;
import spoon.support.JavaOutputProcessor;
import spoon.support.sniper.SniperJavaPrettyPrinter;

public abstract class SoraldAbstractRepair {
    protected final GitPatchGenerator generator = new GitPatchGenerator();
    protected SoraldConfig config;
    protected int patchedFileCounter = 0;

    public SoraldAbstractRepair(SoraldConfig config) {
        this.config = config;
        if (this.config.getGitRepoPath() != null) {
            this.generator.setGitProjectRootDir(this.config.getGitRepoPath());
        }
    }

    public abstract void repair();

    protected void createPatches(String patchedFilePath, JavaOutputProcessor javaOutputProcessor) {
        File patchDir = new File(this.config.getWorkspace() + File.separator + Constants.PATCHES);

        if (!patchDir.exists()) {
            patchDir.mkdirs();
        }
        List<File> list = javaOutputProcessor.getCreatedFiles();
        if (!list.isEmpty()) {
            String outputPath = list.get(list.size() - 1).getAbsolutePath();
            generator.generate(
                    patchedFilePath,
                    outputPath,
                    patchDir.getAbsolutePath()
                            + File.separator
                            + Constants.PATCH_FILE_PREFIX
                            + this.patchedFileCounter);
            this.patchedFileCounter++;
        }
    }

    protected Launcher initLauncher(Launcher launcher, String outputDirPath) {
        launcher.setSourceOutputDirectory(outputDirPath);
        launcher.getEnvironment().setAutoImports(true);
        launcher.getEnvironment().setIgnoreDuplicateDeclarations(true);
        if (this.config.getPrettyPrintingStrategy() == PrettyPrintingStrategy.SNIPER) {
            launcher.getEnvironment()
                    .setPrettyPrinterCreator(
                            () -> {
                                SniperJavaPrettyPrinter sniper =
                                        new SniperJavaPrettyPrinter(launcher.getEnvironment());
                                sniper.setIgnoreImplicit(false);
                                return sniper;
                            });
            launcher.getEnvironment().setCommentEnabled(true);
            launcher.getEnvironment().useTabulations(true);
            launcher.getEnvironment().setTabulationSize(4);
        }
        launcher.buildModel();
        return launcher;
    }

    protected SoraldAbstractProcessor createBaseProcessor(Integer ruleKey) {
        try {
            Class<?> processor = Processors.getProcessor(ruleKey);
            if (processor != null) {
                Constructor<?> cons = processor.getConstructor();
                SoraldAbstractProcessor object = (SoraldAbstractProcessor) cons.newInstance();
                return object;
            }
        } catch (InstantiationException
                | IllegalAccessException
                | InvocationTargetException
                | NoSuchMethodException e) {
            e.printStackTrace();
        }
        return null;
    }
}