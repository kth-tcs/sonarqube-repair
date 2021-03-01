/*
Test to ensure that enclosing abstract class is not considered for processing, as it's an exception
from the rule.
 */

import java.io.Serializable;

public abstract class NestedInAbstract implements Serializable {
    public static class Serial implements Serializable { // Noncompliant
    }
}
