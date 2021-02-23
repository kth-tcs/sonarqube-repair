/*
This test case asserts that Sorald doesn't remove a variable declaration whose initializer is
a dead store, if that variable is later used.
 */

public class DeadStoreInitializer {

    /**
     * A dead store that is directly succeded by another assignment.
     */
    public int deadStoreOnInitializer() {
        int a = 2; // Noncompliant
        a = 3;
        return a;
    }

    /**
     * A dead store where the next assignment is far removed in a nested block.
     */
    public int deadStoreOnInitializerWithVariableUsedInNestedBlock(int a, int b) {
        int c = a; // Noncompliant

        if (a < b) {
            return a;
        } else {
            if (b < a) {
                return b;
            } else {
                c = a + b;
                return c;
            }
        }
    }
}