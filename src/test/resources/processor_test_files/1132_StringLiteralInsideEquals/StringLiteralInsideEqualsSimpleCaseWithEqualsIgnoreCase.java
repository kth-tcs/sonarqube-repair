/*
Test the simple case with equalsIgnoreCase(java.lang.String): the target and the argument of the call should be swapped.
 */

public class StringLiteralInsideEqualsSimpleCaseWithEqualsIgnoreCase {
    public static void main(String[] args) {
        String myString = null;

        System.out.println("Equal? " + myString.equalsIgnoreCase("foo")); // Noncompliant; will raise a NPE
    }
}
